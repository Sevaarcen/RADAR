#!/usr/bin/python3
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

import sys

import cyber_radar.constants as const
from cyber_radar.client_uplink_connection import UplinkConnection
from cyber_radar.system_command import SystemCommand
from cyber_radar.automation_managers import CommandParserManager, PlaybookManager


def main(raw_command: str):
    print('============ EXECUTING COMMAND ============', file=sys.stderr)
    system_command = SystemCommand(raw_command, additional_meta={"run-mode": "manual"})
    # For each yielded value, print it or use it as a control message
    for output_value in system_command.run():
        if isinstance(output_value, str):
            print(output_value)
        else:  # Is bool = end of command and is the result
            if not output_value:
                print("!!!  Command didn't finish executing", file=sys.stderr)
                exit(1)
            if system_command.command_return_code != 0:
                print(f"!#!  Command returned a non-0 return code ({system_command.command_return_code})")
                
            # Else it was sucessful and we can just continue
    print('========== PARSING COMMAND OUTPUT =========', file=sys.stderr)
    parser_manager = CommandParserManager()
    command_json = system_command.to_json()
    metadata, targets = parser_manager.parse(system_command)  # Conditionally parse command

    print('============ RUNNING PLAYBOOKS ============', file=sys.stderr)
    playbook_manager = PlaybookManager()
    playbook_manager.automate(targets)  # Conditionally run Playbooks

    print('========= ESTABLISHING RADAR UPLINK =======', file=sys.stderr)
    uplink = UplinkConnection()

    print('=============== SYNCING DATA ==============', file=sys.stderr)
    print("> command data... ", end='', file=sys.stderr)
    uplink.send_data(const.DEFAULT_COMMAND_COLLECTION, command_json)
    print("done", file=sys.stderr)
    print("> metadata... ", end='', file=sys.stderr)
    uplink.send_data(const.DEFAULT_METADATA_COLLECTION, metadata)
    print("done", file=sys.stderr)
    print("> target data... ", end='', file=sys.stderr)
    if len(targets) != 0:
        uplink.send_data(const.DEFAULT_TARGET_COLLECTION, targets)
        print("done", file=sys.stderr)
    else:
        print("n/a", file=sys.stderr)

    print('============<({[ COMPLETED ]})>============', file=sys.stderr)


if __name__ == '__main__':
    if len(sys.argv) <= 1:
        print(f"USAGE: {sys.argv[0]} <command>")
        exit(1)
    command = ' '.join(sys.argv[1:])
    print(f"Received command (make sure there isn't shell quoting issues): '{command}'", file=sys.stderr)
    try:
        main(command)
    except KeyboardInterrupt:
        print("Received key interrupt... shutting down")
        exit(-1)
