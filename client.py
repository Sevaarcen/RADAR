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
import json
from multiprocessing import Process
from importlib import reload
import radar.utils as utils
from radar.objects import SystemCommand, ServerConnection
from radar.managers import CommandParserManager


INTERCEPT_COMMANDS = [
    "exit",
    "cd",
    "radar"
]

# Global variables
radar_prompt = "[RADAR PROMPT GOES HERE]"
server_process = None
server_connection = None


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


def startup(server_hostname: str):
    """ This method will verify if a RADAR control server is reachable at the specified IP address.
    This method will request authorization from the server if the client doesn't already have authorization.
    :param server_hostname: The IP address or domain-name of the RADAR Control Server
    :return: None
    """
    global server_connection
    server_connection = ServerConnection(server_hostname)
    server_connection.open_connection(attempt_https=True)

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
    utils.run_radar_command('radar mission_list', server_connection)
    print()
    join_mission_name = input("Which mission name do you want to join/create?: ")
    utils.run_radar_command(f'radar mission_join {join_mission_name.strip()}', server_connection)


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
            utils.run_radar_command(command, server_connection)
        else:
            print(f"!!!  Your command was intercepted by RADAR but wasn't processed: {command}")
    except IndexError:
        pass


def start_local_server():
    """ Starts an instance of the RADAR Control Server using it's default configuration on localhost.
    The server will save it's output in the 'server.log' file.
    :return: None
    """
    print("###  Starting local RADAR Control Server (http://localhost:1794)...")
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
    while True:
        try:
            user_input = str(input(radar_prompt)).strip()
        except KeyboardInterrupt:
            print()
            continue

        # Ignore blank input
        if len(user_input) == 0:
            continue

        # Reload the utils module so the program doesn't need to be restarted on changes
        reload(utils)

        # Check if command should be processed differently from a system command
        if any(int_cmd == user_input.split(' ')[0] for int_cmd in INTERCEPT_COMMANDS):
            process_intercepted_command(user_input)
            continue

        system_command = SystemCommand(user_input)  # Setup command to run
        system_command.run()  # Execute command
        parsed_results = parser_manager.parse(system_command)
        print(json.dumps(parsed_results, indent=4, sort_keys=True))
        server_connection.send_raw_command_output(system_command)  # Sync w/ database
        print(system_command.command_output, end='')  # Print command output as it would normally appear


def main():
    """ This method handles initial startup of the RADAR client.
    :return: None
    """
    # Handle client arguments
    parser = argparse.ArgumentParser()
    server_arg_group = parser.add_mutually_exclusive_group(required=True)
    server_arg_group.add_argument('--start-local', dest='start_local_server', action="store_true",
                                  help="Start a local instance of the RADAR Control Server and run on localhost")
    server_arg_group.add_argument('-s', '--server', dest='server', type=str,
                                  help="Connect to a running RADAR Control Server (hostname or IP)")
    parser.add_argument('--trusted-ca', dest='trusted_certificate', type=str,
                        help="Specify a certificate that can be used to verify self-signed SSL certificates")

    arguments = parser.parse_args()

    # Process request to start local server
    if arguments.start_local_server:
        arguments.server = 'localhost'
        global server_process
        server_process = Process(target=start_local_server, daemon=True)
        server_process.start()
        time.sleep(1)

    # If a trusted cert if specified, add it to the environment variables to verify HTTP requests
    if arguments.trusted_certificate:
        absolute_path = os.path.abspath(arguments.trusted_certificate)
        os.environ['REQUESTS_CA_BUNDLE'] = absolute_path

    # Run Commands
    greeting()
    startup(arguments.server)
    client_loop()


if __name__ == '__main__':
    main()
