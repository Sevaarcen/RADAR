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
import multiprocessing
import radar.utils as utils


PROMPT = "[RADAR PROMPT]"

INTERCEPT_COMMANDS = [
    "exit",
    "cd",
    "radar"
]

# SERVER URLs
SERVER_BASE_URL = ''


def update_prompt():
    global PROMPT
    PROMPT = f"[RADAR] {os.getcwd()} > "


def greeting():
    print()
    print('  / ')
    print(' |--   Hello there, welcome to the Red-team Analysis,')
    print(' X\\    Documentation, and Automation Revolution!')
    print('XXX ')
    print()

# TODO fix the exit functions, doesn't kill local server
def goodbye():
    print()
    print('  / ')
    print(' |--   Thanks for participating in the Red-team Analysis,')
    print(' X\\    Documentation, and Automation Revolution!')
    print('XXX ')
    sys.exit(0)


def connect_to_server(ip_address):
    global SERVER_BASE_URL
    SERVER_BASE_URL = f'http://{ip_address}:1794'
    utils.request_authorization(SERVER_BASE_URL)


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
        command_split = command.split(' ', 2)
        radar_command = command_split[1]
        radar_command_arguments = command_split[2]
        if radar_command == 'server':
            print(f"Connected to server at: {SERVER_BASE_URL}")
        elif radar_command == 'db_list':
            split_args = radar_command_arguments.split(' ')
            database = split_args[0]
            collection = split_args[1]
            utils.list_database_contents(SERVER_BASE_URL, database, collection)
        else:
            print('!!! Unknown radar command')
    else:
        print(f"!!!  Your command was intercepted but wasn't processed: {command}")


def main():
    connect_to_server(sys.argv[1])
    # TODO request user authorization, save data in database, make radar commands to view command history

    greeting()
    update_prompt()
    while True:
        user_input = str(input(PROMPT)).strip()
        program = user_input.split(' ', 1)[0]

        # Check if command should be processed differently from a system command
        if any(int_cmd in user_input for int_cmd in INTERCEPT_COMMANDS):
            process_intercepted_command(user_input)
            continue

        # Else run command through system shell
        command_results = utils.run_system_command(user_input)
        # TODO change the way the data is sent
        utils.send_raw_command_output(SERVER_BASE_URL, user_input, command_results)
        print(command_results, end='')  # Print file as it appears


def start_local_server():
    print("###  Starting local RADAR Control Server (http://localhost:1794)...")
    os.system('python server.py 2> server.log')


if __name__ == '__main__':
    if len(sys.argv) != 2:
        print(f"USAGE: python {sys.argv[0]} <server_ip_address>")
        sys.exit(-1)
    # TODO Make this a command-line argument to start local server
    if sys.argv[1] == '!start_local':
        sys.argv[1] = 'localhost'
        proc = multiprocessing.Process(target=start_local_server)
        proc.start()
        time.sleep(3)
    main()




