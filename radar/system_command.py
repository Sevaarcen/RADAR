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

import tempfile
import subprocess
import time


class SystemCommand:

    def __init__(self, command: str):
        self.command = command
        self.command_output = None
        self.execution_time_start = None
        self.execution_time_end = None

    def to_json(self):
        return self.__dict__

    def run(self) -> bool:
        result = True
        self.execution_time_start = time.time()
        # Prepare temporary file to store command output
        temp_output_file = tempfile.NamedTemporaryFile(prefix='tmp', suffix='.out', delete=True)
        try:
            # Run a command and pipe stdout and stderr to the temp file
            subprocess.run(self.command, shell=True, stdout=temp_output_file, stderr=temp_output_file)

            temp_output_file.seek(0)  # Set head at start of file
            contents = temp_output_file.read().decode("utf-8")  # Read contents and decode as text
            temp_output_file.close()  # Then close the file (and delete it)
            self.command_output = contents
            self.execution_time_end = time.time()
        except (KeyboardInterrupt, UnboundLocalError):
            print("!!!  Command cancelled by key interrupt")
            result = False
        return result
