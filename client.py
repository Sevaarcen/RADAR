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
import signal
import time
from multiprocessing import Process
from importlib import reload
import radar.utils as utils


INTERCEPT_COMMANDS = [
    "exit",
    "cd",
    "radar"
]

# Global variables
radar_prompt = "[RADAR PROMPT GOES HERE]"
server_process = None
server_base_url = ''


def update_prompt():
    global radar_prompt
    radar_prompt = f"[RADAR] {os.getcwd()} > "


def greeting():
    print()
    print('     / ')
    print('    |--   Hello there, welcome to the Red-team Analysis,')
    print('    X\\    Documentation, and Automation Revolution!')
    print('   XXX ')
    print()


# TODO fix the exit functions, doesn't kill local server
def goodbye():
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


def connect_to_server(ip_address):
    global server_base_url
    server_base_url = f'http://{ip_address}:1794'
    server_online = False
    max_attempts = 10
    for attempt in range(1, max_attempts + 1):
        print(f'###  Checking if server is online: attempt {attempt}/{max_attempts}')
        server_online = utils.is_server_online(server_base_url)
        if server_online:
            print(f'$$$ Connected to server at: {server_base_url}')
            break
        else:
            time.sleep(1)
    if not server_online:
        print('!!!  Unable to connect to RADAR control server, shutting down')
        sys.exit(1)

    if not utils.get_authorization(server_base_url)[0]:
        utils.request_authorization(server_base_url)


def process_intercepted_command(command):
    """ This function handles how certain commands are processed that are not run as system commands.
    :param command: command as intercepted
    :return: N/A
    """
    if command == 'exit':
        goodbye()

    elif 'cd' in command:
        directory = ""
        try:
            directory = command.split(' ', 1)[1]
            os.chdir(directory)
            update_prompt()
        except (IndexError, FileNotFoundError):
            print(f"!!!  Invalid directory: '{directory}'")

    elif 'radar' in command:
        utils.run_radar_command(command, server_base_url)

    else:
        print(f"!!!  Your command was intercepted but wasn't processed: {command}")


def start_local_server():
    print("###  Starting local RADAR Control Server (http://localhost:1794)...")
    log_file = open('server.log', 'w')
    import server
    server.start(use_stdout=log_file, use_stderr=log_file)


def client_loop():
    update_prompt()
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
        if any(int_cmd in user_input for int_cmd in INTERCEPT_COMMANDS):
            process_intercepted_command(user_input)
            continue

        reload(utils)  # Reload the utils module so the program doesn't need to be restarted on changes
        command_results = utils.run_system_command(user_input)  # Run command through user's shell

        # TODO change the way the data is sent
        utils.send_raw_command_output(server_base_url, user_input, command_results)
        print(command_results, end='')  # Print file as it appears


def main():
    if len(sys.argv) != 2:
        print(f"USAGE: python {sys.argv[0]} <server_ip_address>")
        sys.exit(-1)

    # Process request to start local server
    if sys.argv[1] == '!start_local':
        sys.argv[1] = 'localhost'
        global server_process
        server_process = Process(target=start_local_server, daemon=True)
        server_process.start()
        time.sleep(1)

    # Run Commands
    greeting()
    connect_to_server(sys.argv[1])
    client_loop()


if __name__ == '__main__':
    main()
