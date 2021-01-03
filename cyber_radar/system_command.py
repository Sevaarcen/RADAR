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

import subprocess
import time
import socket
import sys
import os
import uuid


class SystemCommand:

    def __init__(self, command: str, additional_meta=None):
        self.command = command
        self.stdout = ""
        self.stderr = ""
        self.command_output = ""
        self.execution_time_start = None
        self.execution_time_end = None
        self.executed_on_host = socket.getfqdn()
        self.executed_on_ipaddr = socket.gethostbyname(self.executed_on_host)
        self.current_working_directory = os.getcwd()
        if additional_meta:
            self.additional_meta = additional_meta
        self.uuid = str(uuid.uuid4())  # Generate an UUID for internal use and finding this command later in the DB

    def to_json(self):
        return self.__dict__

    def run(self):
        result = True
        self.execution_time_start = time.time()
        try:
            # Run a command and attach stdin to subprocess to allow user interaction
            # Create pipes for stdout and stderr so we can process them manually
            subproc = subprocess.Popen(self.command, shell=True, stdin=sys.stdin, stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)
            # While process is running, stream output to console and relevant variables
            
            while subproc.poll() == None:
                for stdout_line in subproc.stdout:
                    self.stdout += stdout_line
                    self.command_output += stdout_line
                    yield stdout_line.strip()
                for stderr_line in subproc.stderr:
                    self.stderr += stderr_line
                    self.command_output += stderr_line
                    yield stderr_line.strip()
            # Record final variables
            self.command_return_code = subproc.wait()
            self.execution_time_end = time.time()
        # In case user cancelled w/ Ctrl + C or similar
        except (KeyboardInterrupt, UnboundLocalError):
            print("!!!  Command cancelled by key interrupt")
            result = False
        return result
