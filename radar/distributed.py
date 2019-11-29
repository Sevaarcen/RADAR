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

from radar.system_command import SystemCommand
from radar.uplink_server_connection import ServerConnection
from radar.automation_managers import CommandParserManager, PlaybookManager
from radar.client_configuration_manager import ClientConfigurationManager
import radar.constants as const
import threading
import time


class DistributedWatcher:
    def __init__(self, server_connection: ServerConnection, watch_interval=None):
        self.server_connection = server_connection
        if not watch_interval:
            watch_interval = ClientConfigurationManager().config.get("distributed-watch-interval", 60)
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
        system_command = SystemCommand(response)
        command_completed = system_command.run()
        if not command_completed:
            print(f"!!!  Error while running distributed command: {response}")
            return

        # Get command output, parse it, and run playbooks
        command_json = system_command.to_json()
        metadata, targets = self.__parser_manager.parse(system_command)
        self.__playbook_manager.automate(targets, silent=True)

        # Silently sync to DB
        self.server_connection.send_to_database(const.DEFAULT_COMMAND_COLLECTION, command_json)
        self.server_connection.send_to_database(const.DEFAULT_METADATA_COLLECTION, metadata)
        if len(targets) != 0:
            self.server_connection.send_to_database(const.DEFAULT_TARGET_COLLECTION, targets)

        # Run again without waiting if finished
        self.__run_loop_once()

    def __run_loop(self):
        while True:
            self.__run_loop_once()
            time.sleep(self.interval)
