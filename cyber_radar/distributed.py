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
import threading
import time

import cyber_radar.constants as const

from cyber_radar.system_command import SystemCommand
from cyber_radar.uplink_server_connection import ServerConnection
from cyber_radar.automation_managers import CommandParserManager, PlaybookManager
from cyber_radar.client_configuration_manager import ClientConfigurationManager


class DistributedWatcher:
    def __init__(self, queue_add_func: 'function', server_connection: ServerConnection, watch_interval=60):
        self.queue_add_func = queue_add_func
        self.server_connection = server_connection
        self.interval = watch_interval
        self.__parser_manager = CommandParserManager()
        self.__playbook_manager = PlaybookManager()

    def start(self):
        thread = threading.Thread(target=self.__run_loop)
        thread.daemon = True
        thread.start()

    def __run_loop_once(self):
        response = self.server_connection.get_distributed_command()
        if not response:
            return
        print(f"$$$  Received distributed command: '{response}'")
        system_command = SystemCommand(response, additional_meta={"run-mode": "distributed"})
        command_completed = system_command.run(silent=True)  # Run w/o yielding output

        # Get command output, parse it, and run playbooks
        command_json = system_command.to_json()
        metadata, targets = self.__parser_manager.parse(system_command)
        self.__playbook_manager.automate(targets, silent=True)

        # Silently sync to DB using provided callback command
        # If this fails, just crash and propogate error - this function is not dynamic
        self.queue_add_func(const.DEFAULT_COMMAND_COLLECTION, command_json)
        self.queue_add_func(const.DEFAULT_METADATA_COLLECTION, metadata)
        if len(targets) != 0:
            self.queue_add_func(const.DEFAULT_TARGET_COLLECTION, targets)

        # Run again without waiting if finished
        self.__run_loop_once()

    def __run_loop(self):
        while True:
            self.__run_loop_once()
            time.sleep(self.interval)
