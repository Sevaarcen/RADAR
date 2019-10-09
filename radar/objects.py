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
import base64
import getpass
import json
import sys
import tempfile
import subprocess
import requests


class SystemCommand:

    def __init__(self, command: str):
        self.command = command
        self.command_output = None

    def to_json(self):
        return self.__dict__

    def run(self):
        # Prepare temporary file to store command output
        temp_output_file = tempfile.NamedTemporaryFile(prefix='tmp', suffix='.out', delete=True)

        # Run a command and pipe stdout and stderr to the temp file
        subprocess.run(self.command, shell=True, stdout=temp_output_file, stderr=temp_output_file)

        temp_output_file.seek(0)  # Set head at start of file
        contents = temp_output_file.read().decode("utf-8")  # Read contents and decode as text
        temp_output_file.close()  # Then close the file (and delete it)
        self.command_output = contents


class ServerConnection:

    DEFAULT_COMMAND_COLLECTION = 'raw-commands'

    def __init__(self, server_url: str):
        self.server_url = server_url
        self.key = None
        self.mission = 'unassigned'

    def is_connected(self):
        """ Connects to the server and checks the HTTP status code
            :return: True if the status code is 200, else False
            """
        full_request_url = f'{self.server_url}/'
        request = requests.get(full_request_url)
        return request.status_code == 200

    def get_authorization(self):
        """ Returns information about the client's authorization level
        :return: A tuple containing two booleans - is_authorized and is_superuser
        """
        full_request_url = f'{self.server_url}/info/authorized'
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

    def get_mission_list(self):
        full_request_url = f'{self.server_url}/info/missions'
        request = requests.get(full_request_url)
        if request.status_code != 200:
            print(f"!!!  HTTP Code: {request.status_code}")
            response = request.text
            print(response)
            sys.exit(1)
        else:
            response = request.text
            mission_list = response.split(',')
            return mission_list

    def request_authorization(self):
        """ Sends a request to authorize the client based on their current username
        :param server_url: The RADAR Control Server
        :return: None
        """
        username = getpass.getuser()
        full_request_authorization_url = f'{self.server_url}/clients/request?username={username}'
        request = requests.get(full_request_authorization_url)
        if request.status_code != 200:
            print(f"!!!  HTTP Code: {request.status_code}")
            response = request.text
            print(response)
            sys.exit(1)
        else:
            print(f"Requested authorization: {username}@{self.erver_url}")

    # TODO send async multi-processed like server
    def send_raw_command_output(self, system_command: SystemCommand):
        """ Send the command and command results to the server to be inserted into the Mongo database
        :param system_command: The SystemCommand object to sync
        :return: None
        """
        json_data = system_command.to_json()
        base64_json = base64.b64encode(json.dumps(json_data).encode('utf-8'))
        full_insert_url = f'{self.server_url}/database/{self.mission}/{self.DEFAULT_COMMAND_COLLECTION}/insert'
        request = requests.post(full_insert_url, data=base64_json)
        if request.status_code != 200:
            print(f"!!!  HTTP Code: {request.status_code}")
            response = request.text
            print(response)
        else:
            print('... command synced w/ RADAR Control Server database')

    def list_database_contents(self, collection: str):
        """ List the contents of one of the database collections from the server in JSON
        :param collection: The name of the collection you want to view from the current mission
        :return: None
        """
        full_list_url = f'{self.server_url}/database/{self.mission}/{collection}/list'
        request = requests.get(full_list_url)
        if request.status_code != 200:
            print(f"!!!  HTTP Code: {request.status_code}")
            response = request.text
            print(response)
        else:
            response = request.json()
            print(json.dumps(response, indent=4, sort_keys=True))

