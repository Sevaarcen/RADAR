#  This file is part of RADAR.
#  Copyright (C) 2019 Cole Daubenspeck
#
#  RADAR is free software: you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation, either version 3 of the License, or
#  (at your option) any later version.
#
#  RADAR is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with RADAR.  If not, see <https://www.gnu.org/licenses/>.

import os
import sys
import time
import argparse
from multiprocessing import Process
import radar.radar_internals as internals
import radar.constants as const
from radar.objects import SystemCommand, ServerConnection
from radar.managers import *


INTERCEPT_COMMANDS = [
    "exit",
    "cd",
    "radar"
]

# Global variables
radar_prompt = "[RADAR PROMPT GOES HERE]"
client_config = {}
server_process = None
server_connection: ServerConnection = None


def update_prompt():
    """ This method updates the prompt with the current working directory
    :return: None
    """
    global radar_prompt
    radar_prompt = f"[RADAR] {os.getcwd()} > "


def greeting():
    """ This method prints out the welcome when starting the program
    :return: None
    """
    print()
    print('     / ')
    print('    |--   Hello there, welcome to the Red-team Analysis,')
    print('    X\\    Documentation, and Automation Revolution!')
    print('   XXX ')
    print()


def goodbye():
    """ This method kills the local server if it's running and prints the exit message
    :return: None
    """
    global server_process
    if server_process:
        print('###  Shutting down local server...')
        server_process.terminate()  # Kill server process
        server_process.join()  # Then wait for it to die
        if server_process.is_alive():
            print("!!!  Unable to shut down server")
        else:
            print('... done')

    print()
    print('     / ')
    print('    |--   Thanks for participating in the Red-team Analysis,')
    print('    X\\    Documentation, and Automation Revolution!')
    print('   XXX ')
    print()

    sys.exit(0)


def startup():
    """ This method will verify if a RADAR control server is reachable at the specified IP address.
    This method will request authorization from the server if the client doesn't already have authorization.
    :param server_hostname: The IP address or domain-name of the RADAR Control Server
    :return: None
    """
    global server_connection
    server_connection = ServerConnection()
    server_connection.open_connection()

    if not server_connection.get_authorization()[0]:
        server_connection.request_authorization()

    # Check if the user is authorized, else wait until the user becomes authorized
    while True:
        authorized, su_authorized = server_connection.get_authorization()
        if authorized and su_authorized:
            print("$$$  You are authorized as a superuser")
            break
        elif authorized:
            print("$$$ You are authorized")
            break
        else:
            try_again_in = 3
            print(f"You are awaiting authorization for your client: {server_connection.username}")
            print(f"... Trying again in {try_again_in} seconds")
            time.sleep(try_again_in)

    # Join a mission by default, or create a mission if it doesn't exist
    print()
    print("Available missions")
    internals.run_radar_command('radar mission_list', server_connection)
    print()
    join_mission_name = input("Which mission name do you want to join/create?: ")
    internals.run_radar_command(f'radar mission_join {join_mission_name.strip()}', server_connection)


def process_intercepted_command(command):
    """ This function handles how certain commands are processed that are not run as system commands.
    :param command: command as intercepted
    :return: None
    """
    try:
        command_word = command.split(' ')[0]
        if command_word == 'exit':
            goodbye()

        elif command_word == 'cd':
            directory = ""
            try:
                directory = command.split(' ', 1)[1]
                os.chdir(directory)
                update_prompt()
            except (IndexError, FileNotFoundError):
                print(f"!!!  Invalid directory: '{directory}'")

        elif command_word == 'radar':
            global server_connection
            internals.run_radar_command(command, server_connection)
        else:
            print(f"!!!  Your command was intercepted by RADAR but wasn't processed: {command}")
    except IndexError:
        pass


def start_local_server():
    """ Starts an instance of the RADAR Control Server using it's default configuration on localhost.
    The server will save it's output in the 'server.log' file.
    :return: None
    """
    print("###  Starting local RADAR Control Server...")
    log_file = open('server.log', 'w')
    import server
    server.start(use_stdout=log_file, use_stderr=log_file)


def client_loop():
    """ This is the main loop functionality of RADAR. It shows the command prompt and takes user input.
    :return: None
    """
    update_prompt()
    global server_connection
    parser_manager = CommandParserManager()
    playbook_manager = PlaybookManager()
    while True:
        try:
            user_input = str(input(radar_prompt)).strip()
        except KeyboardInterrupt:
            print()
            continue

        # Ignore blank input
        if len(user_input) == 0:
            continue

        # Check if command should be processed differently from a system command
        if any(int_cmd == user_input.split(' ')[0] for int_cmd in INTERCEPT_COMMANDS):
            process_intercepted_command(user_input)
            continue

        system_command = SystemCommand(user_input)  # Setup command to run
        command_completed = system_command.run()  # Execute command
        if command_completed:
            print(system_command.command_output, end='')  # Print command output as it would normally appear

            command_json = system_command.to_json()
            metadata, targets = parser_manager.parse(system_command)  # Conditionally parse command
            print('============ RUNNING PLAYBOOKS ============')
            playbook_manager.automate(targets)  # Conditionally run Playbooks
            print('===========================================')
            # Sync w/ database
            print('###  Syncing data with RADAR Control Server... ', end="")
            server_connection.send_to_database(const.DEFAULT_COMMAND_COLLECTION, command_json)
            server_connection.send_to_database(const.DEFAULT_METADATA_COLLECTION, metadata)
            if len(targets) != 0:
                server_connection.send_to_database(const.DEFAULT_TARGET_COLLECTION, targets)
            print("done")


def main():
    """ This method handles initial startup of the RADAR client.
    :return: None
    """
    # Handle client arguments
    parser = argparse.ArgumentParser()
    server_arg_group = parser.add_mutually_exclusive_group(required=False)
    server_arg_group.add_argument('--start-local',
                                  dest='start_local_server',
                                  action="store_true",
                                  help="Start a local instance of the RADAR Control Server and run on localhost")
    server_arg_group.add_argument('-s', '--server',
                                  dest='server',
                                  type=str,
                                  help="Connect to a running RADAR Control Server (hostname or IP)")
    parser.add_argument('-p',
                        '--port',
                        dest='port',
                        type=int,
                        help="Override default port for RADAR Control Server")
    parser.add_argument('-c',
                        '--config',
                        dest='config_path',
                        type=str,
                        default="client_config.toml",
                        help="Specify non-default configuration file to use")
    parser.add_argument('--trusted-ca',
                        dest='trusted_certificate',
                        type=str,
                        help="Specify a certificate that can be used to verify self-signed SSL certificates")

    arguments = parser.parse_args()

    # Process request to start local server
    if arguments.start_local_server:
        arguments.server = 'localhost'
        global server_process
        server_process = Process(target=start_local_server, daemon=True)
        server_process.start()
        time.sleep(1)

    # Load config file
    config_path = arguments.config_path
    try:
        global client_config
        client_config = toml.load(config_path)
    except FileNotFoundError:
        print(f"!!!  CRITICAL: Could not find configuration file: {config_path}")
        exit(1)

    # Merge with arguments
    client_config_manager = ClientConfigurationManager(config_path=config_path)
    client_config = client_config_manager.config

    if arguments.server:
        client_config.setdefault("server", {})["host"] = arguments.server

    if arguments.port:
        client_config.setdefault("server", {})['port'] = arguments.port

    # If a trusted cert if specified, add it to the environment variables to verify HTTP requests
    if arguments.trusted_certificate:
        absolute_path = os.path.abspath(arguments.trusted_certificate)
        client_config.setdefault("server", {})['CA-certificate'] = absolute_path

    # Verify configuration plus manual options
    if not verify_config(client_config):
        print("!!! Invalid configuration file, missing required components")
        exit(1)

    trusted_ca_certificate = client_config.get('server').get('CA-certificate', None)
    if trusted_ca_certificate:
        os.environ['REQUESTS_CA_BUNDLE'] = trusted_ca_certificate

    # Run Commands
    greeting()
    startup()
    client_loop()


if __name__ == '__main__':
    main()
