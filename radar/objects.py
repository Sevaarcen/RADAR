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
import warnings
from requests.exceptions import ConnectionError, SSLError
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

    def __init__(self, hostname: str, port=1794):
        self.server_url = f'https://{hostname}:{port}'
        self._hostname = hostname
        self._port = port
        self._verify_host = True
        self.username = getpass.getuser()
        self.is_authorized = None
        self.is_superuser = None

        self.key = None
        self.mission = self.DEFAULT_MISSION

    def __str__(self):
        return self.server_url

    def open_connection(self, attempt_https=True):
        if not attempt_https:
            self.server_url = f'http://{self._hostname}:{self._port}'
        print(f'###  Attempting to verify connection to {self.server_url}')
        try:
            try:
                server_online = self.attempt_to_connect(5)
                if server_online:
                    print("$$$ Connected to the RADAR control server")
                elif attempt_https:
                    print("!!!  An HTTPs connection could not be established")
                    try_http = input('Do you want to try using HTTP instead (data will be visible as plain-text) [y/N]?: ')
                    try:
                        if try_http.lower()[0] == 'y':
                            print('###  Attempting HTTP connection instead')
                            self.server_url = f'http://{self._hostname}:{self._port}'
                            http_server_online = self.attempt_to_connect(5)
                            if http_server_online:
                                print("$$$ Connected to the RADAR control server")
                            else:
                                print('$$$  All connection attempts failed, shutting down...')
                                sys.exit(3)
                        else:
                            print('###  The server is untrusted. Please correct the error and restart the client')
                            self._verify_host = True
                    except IndexError:
                        print('$$$  All connection attempts failed, shutting down...')
                        sys.exit(3)
            except SSLError as ssl_error:
                print("!!! The connection encountered an SSL error")
                print(ssl_error)
                trust_input = input('Do you wish to turn off SSL verification - this may allow MiTM attacks [y/N]?: ')
                try:
                    if trust_input.lower()[0] == 'y':
                        print('###  Blindly trusting SSL certificates and suppressing warnings...')
                        warnings.filterwarnings("ignore", message="Unverified HTTPS request is being made. "\
                                                                  "Adding certificate verification is strongly advised. "\
                                                                  "See: https://urllib3.readthedocs.io/en/latest/advanced-usage.html#ssl-warnings")
                        self._verify_host = False
                    else:
                        print('###  The server is untrusted. Please correct the error and restart the client')
                        self._verify_host = True
                        sys.exit(3)
                except IndexError:
                    print('###  The server is untrusted. Please correct the error and restart the client')
                    self._verify_host = True
                    sys.exit(3)
        except KeyboardInterrupt:
            sys.exit(1)

    def attempt_to_connect(self, max_attempts):
        max_attempts = 10
        for attempt in range(1, max_attempts + 1):
            server_online = self.is_connected()
            if server_online:
                return True
            else:
                time.sleep(1)
        if not server_online:
            return False

    def is_connected(self):
        """ Connects to the server and checks the HTTP status code
            :return: True if the status code is 200, else False
            """
        try:
            response = requests.get(self.server_url, verify=self._verify_host)
        except SSLError as ssl_error:
            raise ssl_error
        except ConnectionError:
            return False
        return response.status_code == 200

    def get_authorization(self):
        """ Returns information about the client's authorization level
        :return: A tuple containing two booleans - is_authorized and is_superuser
        """
        full_request_url = f'{self.server_url}/info/authorized'
        request = requests.get(full_request_url, verify=self._verify_host)
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
        request = requests.get(full_request_url, verify=self._verify_host)
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
        response = requests.get(full_request_url, verify=self._verify_host)
        return response.json()

    def get_collection_list(self) -> list:
        full_request_url = f'{self.server_url}/info/database'
        response = requests.get(full_request_url, verify=self._verify_host)
        database_structure = response.json()
        collection_list = database_structure.get(f'{self.MISSION_PREFIX}{self.mission}', [])
        return collection_list

    def request_authorization(self):
        """ Sends a request to authorize the client based on their current username on system
        :return: None
        """
        full_request_authorization_url = f'{self.server_url}/clients/request?username={self.username}'
        request = requests.get(full_request_authorization_url, verify=self._verify_host)
        if request.status_code != 200:
            print(f"!!!  HTTP Code: {request.status_code}")
            response = request.text
            print(response)
            sys.exit(1)
        else:
            print(f"Requested authorization: {self.username}@{self.server_url}")

    def grant_authorization(self, username, superuser=False):
        full_url = f'{self.server_url}/clients/authorize?username={username}&superuser={superuser}'
        request = requests.get(full_url, verify=self._verify_host)
        if request.status_code != 200:
            print(f"!!!  HTTP Code: {request.status_code}")
            response = request.text
            print(response)
            sys.exit(1)
        else:
            print(request.json)

    def send_raw_command_output(self, system_command: SystemCommand):
        """ Send the command and command results to the server to be inserted into the Mongo database
        :param system_command: The SystemCommand object to sync
        :return: None
        """
        json_data = system_command.to_json()
        base64_json = base64.b64encode(json.dumps(json_data).encode('utf-8'))
        full_insert_url = f'{self.server_url}/database/{self.MISSION_PREFIX}{self.mission}/{self.DEFAULT_COMMAND_COLLECTION}/insert'
        request = requests.post(full_insert_url, data=base64_json, verify=self._verify_host)
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
        request = requests.get(full_list_url, verify=self._verify_host)
        if request.status_code != 200:
            print(f"!!!  HTTP Code: {request.status_code}")
            response = request.text
            print(response)
        else:
            response = request.json()
            print(json.dumps(response, indent=4, sort_keys=True))
