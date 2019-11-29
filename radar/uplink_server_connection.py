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
import time
import os
import requests
import logging
from requests.exceptions import ConnectionError, SSLError

import radar.constants as const


class ServerConnection:

    def __init__(self, logger: logging, config: dict):
        self.logger = logger
        self.config = config

        self.sync_interval = self.config.setdefault('sync-interval', 10)

        self._hostname = self.config['server']['host']
        self._port = self.config['server'].setdefault('port', 1794)
        self.server_url = f'https://{self._hostname}:{self._port}'

        self._verify_host = self.config['server'].setdefault('verify-host', True)
        self._username = getpass.getuser()
        self.is_authorized = None
        self.is_superuser = None

        self.api_key = None
        if os.path.exists(const.UPLINK_API_KEY_FILENAME):
            with open(const.UPLINK_API_KEY_FILENAME, 'r') as key_file:
                self.api_key = key_file.read().strip()
                self.logger.info("Loaded API key from file")
        if not self.api_key:
            self.request_authorization()
        self.mission = const.DEFAULT_MISSION

    def __str__(self):
        return self.server_url

    def open_connection(self):
        attempt_https = self.config.get('server').setdefault('attempt-https', True)
        use_https = self.config['server'].setdefault('use-https', False)
        if not use_https:
            self.server_url = f'http://{self._hostname}:{self._port}'
        self.logger.debug(f'Attempting to verify connection to {self.server_url}')
        try:
            try:
                server_online = self.attempt_to_connect(max_attempts=5)
                if server_online:
                    self.logger.info("Connected to the RADAR control server")
                elif attempt_https:
                    self.logger.error("Could not establish HTTPS connection with the RADAR control server")
                    exit(2)
            except SSLError as ssl_error:
                self.logger.error(f"The uplink encountered an SSL error: {ssl_error}")
                exit(2)
        except KeyboardInterrupt:
            exit(1)

    def attempt_to_connect(self, max_attempts=10):
        server_online = False
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
        auth_cookie = {'key': self.api_key}
        req = requests.get(full_request_url, cookies=auth_cookie, verify=self._verify_host)
        if req.status_code != 200:
            self.logger.error(f"HTTP Code received while getting authorization: {req.status_code}")
            response = req.text
            self.logger.debug(response)
            exit(1)
        else:
            response = req.json()
            self.is_authorized = response.get('Authorized', False)
            self.is_superuser = response.get('Superuser', False)
            return self.is_authorized, self.is_superuser

    def get_mission_list(self) -> list:
        """ Returns a list of all missions that exist on the server
        :return: A list of mission names that exist in the radar database
        """

        full_request_url = f'{self.server_url}/info/missions'
        auth_cookie = {'key': self.api_key}
        req = requests.get(full_request_url, cookies=auth_cookie, verify=self._verify_host)
        if req.status_code != 200:
            self.logger.error(f"HTTP Code received while getting mission list: {req.status_code}")
            response = req.text
            self.logger.debug(response)
            exit(1)
        else:
            response = req.text
            mission_list = response.split(',') if len(response) > 0 else []
            if const.DEFAULT_MISSION not in mission_list:
                mission_list.append(const.DEFAULT_MISSION)
            return mission_list

    def get_mongo_structure(self) -> dict:
        full_request_url = f'{self.server_url}/info/database'
        auth_cookie = {'key': self.api_key}
        req = requests.get(full_request_url, cookies=auth_cookie, verify=self._verify_host)
        return req.json()

    def get_collection_list(self) -> list:
        full_request_url = f'{self.server_url}/info/database'
        auth_cookie = {'key': self.api_key}
        req = requests.get(full_request_url, cookies=auth_cookie, verify=self._verify_host)
        database_structure = req.json()
        collection_list = database_structure.get(f'{const.MISSION_PREFIX}{self.mission}', [])
        return collection_list

    def request_authorization(self):
        """ Sends a request to authorize the client based on their current username on system
        :return: None
        """
        full_request_url = f'{self.server_url}/clients/request?username={self._username}'
        auth_cookie = {'key': self.api_key}
        req = requests.get(full_request_url, cookies=auth_cookie, verify=self._verify_host)
        if req.status_code != 200:
            self.logger.error(f"HTTP Code received while requesting authorization: {req.status_code}")
            response = req.text
            self.logger.debug(response)
            exit(1)
        else:
            print(f"Requested authorization: {self._username}@{self.server_url}")
        api_key = req.text
        if api_key:
            try:
                api_key_file = open(const.UPLINK_API_KEY_FILENAME, 'w')
                api_key_file.write(api_key)
                api_key_file.close()
            except PermissionError as pe:
                self.logger.error(f'Could not create api key file: {pe}')
                self.logger.info(self.api_key)

    def modify_authorization(self, username, superuser=False, authorizing=True):
        if authorizing:
            full_request_url = f'{self.server_url}/clients/authorize?key={username}&superuser={superuser}'
        else:
            full_request_url = f'{self.server_url}/clients/deauthorize?key={username}'
        auth_cookie = {'key': self.api_key}
        req = requests.get(full_request_url, cookies=auth_cookie, verify=self._verify_host)
        if req.status_code != 200:
            self.logger.error(f"HTTP Code received while modifying authorization: {req.status_code}")
            response = req.text
            self.logger.debug(response)
            return False
        else:
            self.logger.info(req.text)
            return True

    def send_to_database(self, collection: str, data: (list, dict)):
        """ Send the command and command results to the server to be inserted into the Mongo database
        :param collection: Which collection to sync the data to (use the constants module)
        :param data: The JSON dict or list of dicts to insert into the database
        :return: A boolean which is True on success
        """
        try:
            print("Send to db being processed")
            print(data)
            print(type(data))
            encoded_data = json.dumps(data).encode('utf-8')
            base64_json = base64.b64encode(encoded_data)
            full_request_url = f'{self.server_url}/database/{const.MISSION_PREFIX}{self.mission}/{collection}/insert'
            auth_cookie = {'key': self.api_key}
            req = requests.post(full_request_url, cookies=auth_cookie, data=base64_json, verify=self._verify_host)
            if req.status_code != 200:
                self.logger.warning(f"HTTP Code received while sending to database: {req.status_code}")
                response = req.text
                self.logger.debug(response)
                return False
            else:
                self.logger.info("Successfully sent data to database")
                return True
        except json.decoder.JSONDecodeError:
            self.logger.warning("Invalid data sent to database, cannot be JSON dumped")
            self.logger.debug(data)
            return False

    def get_database_contents(self, collection: str, database=None):
        """ List the contents of one of the database collections from the server in JSON
        :param collection: The name of the collection you want to view from the current mission
        :param database:
        :return: None
        """
        if not database:
            database = f'{const.MISSION_PREFIX}{self.mission}'
        full_request_url = f'{self.server_url}/database/{database}/{collection}/list'
        auth_cookie = {'key': self.api_key}
        req = requests.get(full_request_url, cookies=auth_cookie, verify=self._verify_host)
        if req.status_code != 200:
            self.logger.error(f"HTTP Code received while getting database contents: {req.status_code}")
            response = req.text
            self.logger.debug(response)
            return None
        else:
            response = req.json()
            return response

    def send_distributed_command(self, command):
        full_request_url = f'{self.server_url}/distributed/add'
        encoded_command = base64.b64encode(command.encode('utf-8'))
        auth_cookie = {'key': self.api_key}
        req = requests.post(full_request_url, cookies=auth_cookie, data=encoded_command, verify=self._verify_host)
        if req.status_code != 200:
            self.logger.error(f"HTTP Code received while sending distributed command: {req.status_code}")
            response = req.text
            self.logger.debug(response)
        else:
            print("###  Command added to queue")

    def get_distributed_command(self):
        full_request_url = f'{self.server_url}/distributed/get'
        auth_cookie = {'key': self.api_key}
        req = requests.get(full_request_url, cookies=auth_cookie, verify=self._verify_host)
        if req.status_code == 200:
            return req.text
        elif req.status_code == 304:
            return None
        else:
            self.logger.error(f"HTTP Code received while getting distributed command: {req.status_code}")
            response = req.text
            self.logger.debug(response)
