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
from requests.exceptions import ConnectionError
import time


class SystemCommand:

    def __init__(self, command: str):
        self.command = command
        self.command_output = None
        self.execution_time_start = None
        self.execution_time_end = None

    def to_json(self):
        return self.__dict__

    def run(self):
        self.execution_time_start = time.time()
        # Prepare temporary file to store command output
        temp_output_file = tempfile.NamedTemporaryFile(prefix='tmp', suffix='.out', delete=True)

        # Run a command and pipe stdout and stderr to the temp file
        subprocess.run(self.command, shell=True, stdout=temp_output_file, stderr=temp_output_file)

        temp_output_file.seek(0)  # Set head at start of file
        contents = temp_output_file.read().decode("utf-8")  # Read contents and decode as text
        temp_output_file.close()  # Then close the file (and delete it)
        self.command_output = contents
        self.execution_time_end = time.time()


class ServerConnection:

    MISSION_PREFIX = "mission-"
    DEFAULT_MISSION = "default"
    DEFAULT_COMMAND_COLLECTION = 'raw-commands'

    def __init__(self, server_url: str):
        self.server_url = server_url
        self.username = getpass.getuser()
        self.is_authorized = None
        self.is_superuser = None

        self.key = None
        self.mission = self.DEFAULT_MISSION

    def is_connected(self):
        """ Connects to the server and checks the HTTP status code
            :return: True if the status code is 200, else False
            """
        full_request_url = f'{self.server_url}/'
        try:
            request = requests.get(full_request_url)
        except ConnectionError:
            return False
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
            self.is_authorized = response.get('Authorized', False)
            self.is_superuser = response.get('Superuser', False)
            return self.is_authorized, self.is_superuser

    def get_mission_list(self) -> list:
        """ Returns a list of all missions that exist on the server
        :return: A list of mission names that exist in the radar database
        """
        full_request_url = f'{self.server_url}/info/missions'
        request = requests.get(full_request_url)
        if request.status_code != 200:
            print(f"!!!  HTTP Code: {request.status_code}")
            response = request.text
            print(response)
            sys.exit(1)
        else:
            response = request.text
            mission_list = response.split(',') if len(response) > 0 else []
            mission_list.append(self.DEFAULT_MISSION)
            return mission_list

    def get_mongo_structure(self) -> dict:
        full_request_url = f'{self.server_url}/info/database'
        response = requests.get(full_request_url)
        return response.json()

    def get_collection_list(self) -> list:
        full_request_url = f'{self.server_url}/info/database'
        response = requests.get(full_request_url)
        database_structure = response.json()
        collection_list = database_structure.get(f'{self.MISSION_PREFIX}{self.mission}', [])
        return collection_list

    def request_authorization(self):
        """ Sends a request to authorize the client based on their current username on system
        :return: None
        """
        full_request_authorization_url = f'{self.server_url}/clients/request?username={self.username}'
        request = requests.get(full_request_authorization_url)
        if request.status_code != 200:
            print(f"!!!  HTTP Code: {request.status_code}")
            response = request.text
            print(response)
            sys.exit(1)
        else:
            print(f"Requested authorization: {self.username}@{self.server_url}")

    def send_raw_command_output(self, system_command: SystemCommand):
        """ Send the command and command results to the server to be inserted into the Mongo database
        :param system_command: The SystemCommand object to sync
        :return: None
        """
        json_data = system_command.to_json()
        base64_json = base64.b64encode(json.dumps(json_data).encode('utf-8'))
        full_insert_url = f'{self.server_url}/database/{self.MISSION_PREFIX}{self.mission}/{self.DEFAULT_COMMAND_COLLECTION}/insert'
        request = requests.post(full_insert_url, data=base64_json)
        if request.status_code != 200:
            print(f"!!!  HTTP Code: {request.status_code}")
            response = request.text
            print(response)
        else:
            print('... command synced w/ RADAR Control Server database')

    def list_database_contents(self, collection: str, database=None):
        """ List the contents of one of the database collections from the server in JSON
        :param collection: The name of the collection you want to view from the current mission
        :param database:
        :return: None
        """
        if not database:
            database = f'{self.MISSION_PREFIX}{self.mission}'
        full_list_url = f'{self.server_url}/database/{database}/{collection}/list'
        request = requests.get(full_list_url)
        if request.status_code != 200:
            print(f"!!!  HTTP Code: {request.status_code}")
            response = request.text
            print(response)
        else:
            response = request.json()
            print(json.dumps(response, indent=4, sort_keys=True))

