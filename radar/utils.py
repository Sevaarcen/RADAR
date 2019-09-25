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
import os
import sys
import requests
import json
import base64


def run_system_command(command):
    """ Runs a system command and returns the output
    :param command: The string to be ran as a system command
    :return: results of that command as it would appear on the command-line
    """
    # Prepare temporary file to store command output
    temp_output_file = tempfile.NamedTemporaryFile(suffix='.out', prefix='tmp', delete=False)
    temp_filepath = temp_output_file.name
    temp_output_file.close()  # Release lock on file by closing it so Python isn't using it

    # Run a command and pipe stdout and stderr to the temp file
    process = os.system(f"{command} 2>&1 1> {temp_filepath}")

    # Grab command output from temp file and print it out
    contents = ""
    with open(temp_filepath, 'r') as temp_output_file:
        contents = temp_output_file.read()
    os.remove(temp_filepath)  # Delete temp file
    return contents


def request_authorization(server_url):
    friendly_name = str(input("What is your name?: "))
    full_request_authorization_url = f'{server_url}/clients/request?username={friendly_name}'
    request = requests.get(full_request_authorization_url)
    if request.status_code != 200:
        print(f"!!!  HTTP Code: {request.status_code}")
        response = request.text
        print(response)
        sys.exit(1)
    else:
        print(f"Requested authorization at {server_url}")


def send_raw_command_output(server_url, command, command_output):
    json_data = {'command': command, 'output': command_output}
    base64_json = base64.b64encode(json.dumps(json_data).encode('utf-8'))
    full_insert_url = f'{server_url}/database/raw/commands/insert'
    request = requests.post(full_insert_url, data=base64_json)
    if request.status_code != 200:
        print(f"!!!  HTTP Code: {request.status_code}")
        response = request.text
        print(response)
    else:
        print('... command synced w/ RADAR Control Server database')


def list_database_contents(server_url, database, collection):
    full_list_url = f'{server_url}/database/{database}/{collection}/list'
    request = requests.get(full_list_url)
    if request.status_code != 200:
        print(f"!!!  HTTP Code: {request.status_code}")
        response = request.text
        print(response)
    else:
        response = request.json()
        print(json.dumps(response, indent=4, sort_keys=True))
