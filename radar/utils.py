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
import sys
import requests
import json
import base64
import getpass


def run_radar_command(command, server_url):
    command_split = command.split(' ', 2)
    if len(command_split) < 2:
        print('!!!  No RADAR command specified')
        return
    radar_command = command_split[1]
    radar_command_arguments = command_split[2] if len(command_split) > 2 else None

    # Process each command
    if radar_command == 'server':
        print(f"Connected to server at: {server_url}")
    elif radar_command == 'db_list':
        if not radar_command_arguments:
            print('!!!  You must specify a database and collection. Usage: radar db_list <database> <collection>')
            return
        split_args = radar_command_arguments.split(' ')
        if len(split_args) != 2:
            print('!!!  You must specify a database and collection. Usage: radar db_list <database> <collection>')
            return
        database = split_args[0]
        collection = split_args[1]
        list_database_contents(server_url, database, collection)
    elif radar_command == 'request_auth':
        print('###  Requesting authorization...')
        request_authorization(server_url)
    elif radar_command == 'check_auth':
        result = get_authorization(server_url)
        if result[1]:
            print('You are authorized as a superuser!')
        elif result[0]:
            print('You are authorized.')
        else:
            print('You are unauthorized, please ask a superuser to authorize you...')
    else:
        return f'!!!  Unknown radar command: {radar_command}'


def run_system_command(command):
    """ Runs a system command and returns the output
    :param command: The string to be ran as a system command
    :return: results of that command as it would appear on the command-line
    """
    # Prepare temporary file to store command output
    temp_output_file = tempfile.NamedTemporaryFile(prefix='tmp', suffix='.out', delete=True)

    # Run a command and pipe stdout and stderr to the temp file
    subprocess.run(command, shell=True, stdout=temp_output_file, stderr=temp_output_file)

    temp_output_file.seek(0)  # Set head at start of file
    contents = temp_output_file.read().decode("utf-8")  # Read contents and decode as text
    temp_output_file.close()  # Then close the file (and delete it)
    return contents


def is_server_online(server_url):
    full_request_url = f'{server_url}/'
    request = requests.get(full_request_url)
    return request.status_code == 200


def get_authorization(server_url):
    full_request_url = f'{server_url}/info/authorized'
    request = requests.get(full_request_url)
    if request.status_code != 200:
        print(f"!!!  HTTP Code: {request.status_code}")
        response = request.text
        print(response)
        sys.exit(1)
    else:
        response = request.json()
        authorized = response.get('Authorized', False)
        su_authorized = response.get('Superuser', False)
        return authorized, su_authorized


def request_authorization(server_url):
    username = getpass.getuser()
    full_request_authorization_url = f'{server_url}/clients/request?username={username}'
    request = requests.get(full_request_authorization_url)
    if request.status_code != 200:
        print(f"!!!  HTTP Code: {request.status_code}")
        response = request.text
        print(response)
        sys.exit(1)
    else:
        print(f"Requested authorization: {username}@{server_url}")


# TODO send async multi-processed like server
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
