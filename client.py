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
import radar.utils as utils
import server
from multiprocessing import Process

PROMPT = "[RADAR PROMPT]"

INTERCEPT_COMMANDS = [
    "exit",
    "cd",
    "radar"
]


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


def goodbye():
    print()
    print('  / ')
    print(' |--   Thanks for participating in the Red-team Analysis,')
    print(' X\\    Documentation, and Automation Revolution!')
    print('XXX ')
    exit(0)


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
        print("!!!  TODO")
    else:
        print(f"!!!  Your command was intercepted but wasn't processed: {command}")


def main():
    # TODO Make this a command-line argument to start local server
    print("###  Starting local RADAR Control Server (http://localhost:1794)...")
    utils.run_system_command('python server.py &')
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
        print(command_results, end='')  # Print file as it appears


if __name__ == '__main__':
    main()
