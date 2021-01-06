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

import cyber_radar.constants as const


class ServerConnection:

    def __init__(self, logger: logging, config: dict):
        self.logger = logger
        self.logger.info("A NEW SERVER UPLINK CONNECTION HAS BEEN MADE")
        self.logger.debug("Starting initialize of connection") #TODO
        self.config = config

        self.logger.debug("Gathering Uplink config settings") #TODO
        self.sync_interval = self.config.setdefault('sync-interval', 10)

        self.__using_https = self.config['server'].setdefault('use-https', False)
        self._hostname = self.config['server']['host']
        self._port = self.config['server'].setdefault('port', 1794)
        self._protocol = "https" if self.__using_https else "http"
        self.server_url = f'{self._protocol}://{self._hostname}:{self._port}'
        self.logger.debug(f"Uplink is using the RADAR Control Server at: {self.server_url}")

        self._verify_host = self.config['server'].setdefault('verify-host', True)
        self._username = getpass.getuser()
        self.is_authorized = None
        self.is_superuser = None

        self.logger.debug("Getting RADAR Control Server API Key") #TODO
        self.api_key = None
        if os.path.exists(const.UPLINK_API_KEY_FILENAME):
            self.logger.debug("Uplink API Key File exists... loading saved key")
            with open(const.UPLINK_API_KEY_FILENAME, 'r') as key_file:
                self.api_key = key_file.read().strip()
                self.logger.info("Successfully loaded API key from file")
        if not self.api_key:
            self.logger.debug("Uplink API Key File doesn't exist... requesting authorization")
            self.request_authorization()

    def __str__(self):
        return self.server_url

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

    def get_collection_list(self, database) -> dict:
        full_request_url = f'{self.server_url}/info/database'
        auth_cookie = {'key': self.api_key}
        req = requests.get(full_request_url, cookies=auth_cookie, verify=self._verify_host)
        database_structure = req.json()
        collection_list = {}
        collection_list["result"] = database_structure.get(database, [])
        return collection_list

    def request_authorization(self):
        """ Sends a request to authorize the client based on their current username on system
        :return: None
        """
        full_request_url = f'{self.server_url}/clients/request?username={self._username}'
        req = requests.get(full_request_url, verify=self._verify_host)
        self.logger.debug(repr(req))
        if req.status_code != 200:
            self.logger.error(f"HTTP Code received while requesting authorization: {req.status_code}")
            response = req.text
            self.logger.debug(response)
            exit(1)
        else:
            self.logger.info(f"Requested authorization: {self._username}@{self.server_url}")
        self.api_key = req.text
        if self.api_key:
            try:
                api_key_file = open(const.UPLINK_API_KEY_FILENAME, 'w')
                api_key_file.write(self.api_key)
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

    def send_to_database(self, mission: str, collection: str, data):
        """ Send the command and command results to the server to be inserted into the Mongo database
        :param mission: Name of mission to store data with
        :param collection: Which collection to sync the data to (use the constants module)
        :param data: The JSON dict or list of dicts to insert into the database
        :return: A boolean which is True on success
        """
        try:
            self.logger.debug(f"The following data is being send to database collection: '{const.MISSION_PREFIX}{mission}' '{collection}'")
            self.logger.debug(data)
            encoded_data = json.dumps(data).encode('utf-8')
            base64_json = base64.b64encode(encoded_data)
            full_request_url = f'{self.server_url}/database/{const.MISSION_PREFIX}{mission}/{collection}/insert'
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

    def bulk_send_data(self, data: dict):
        """ For any number of documents, send to RADAR Control Server for insertion into the database.

        Args:
            data (dict): dict where keys are DB names, values are dicts containing collection names as keys and document list as values.

        Returns:
            str: None on error else message of result
        """
        self.logger.debug("Sending bulk data to RADAR Control Server")
        full_request_url = f"{self.server_url}/database/bulk-insert"
        auth_cookie = {'key': self.api_key}
        req = requests.post(full_request_url, json=data, cookies=auth_cookie, verify=self._verify_host)
        if req.status_code != 200:
            self.logger.error(f"HTTP Code received while bulk inserting database contents: {req.status_code}")
            response = req.text
            self.logger.debug(response)
            return False
        else:
            response = req.text
            return response

    def get_database_contents(self, database: str, collection: str):
        """ List the contents of one of the database collections from the server in JSON
        :param database: The full name of the database you want to view
        :param collection: The name of the collection you want to view from the current mission
        :return: None
        """
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
    
    def query_database(self, database: str, collection: str, filter: dict):
        """List the contents of one of the database collections from the server in JSON using a given filter
        :param database: The full name of the database you want to view
        :param collection: The name of the collection you want to view from the current mission
        :return: None
        """
        full_request_url = f'{self.server_url}/database/{database}/{collection}/list'
        auth_cookie = {'key': self.api_key}
        req = requests.post(full_request_url, json=filter, cookies=auth_cookie, verify=self._verify_host)
        if req.status_code != 200:
            self.logger.error(f"HTTP Code received while getting database contents: {req.status_code}")
            response = req.text
            self.logger.debug(response)
            return None
        else:
            response = req.json()
            return response
    
    def pop_shared_data(self, database: str, collection: str, filter: dict) -> dict:
        """[summary]

        Args:
            database (str): Current mission
            collection (str): Name of shared collection
            filter (dict): What data to pop
        
        Returns:
            dict of popped data
        """
        full_request_url = f'{self.server_url}/database/{database}/{collection}/pop'
        auth_cookie = {'key': self.api_key}
        req = requests.post(full_request_url, json=filter, cookies=auth_cookie, verify=self._verify_host)
        if req.status_code != 200:
            self.logger.error(f"HTTP Code received while popping shared collection contents: {req.status_code}")
            response = req.text
            self.logger.debug(response)
            return {}
        else:
            response = req.json()
            return response


    def send_distributed_commands(self, command_list):
        if not isinstance(command_list, list):
            self.logger.error(f'Cannot send distributed commands, it is not a list. It is a {type(command_list)} object')
        full_request_url = f'{self.server_url}/distributed/add'
        auth_cookie = {'key': self.api_key}
        req = requests.post(full_request_url, cookies=auth_cookie, json=command_list, verify=self._verify_host)
        if req.status_code != 200:
            self.logger.error(f"HTTP Code received while sending distributed commands: {req.status_code}")
            response = req.text
            self.logger.debug(response)
        else:
            self.logger.info(f"{len(command_list)} new distributed commands added to queue")

    def get_distributed_command(self) -> dict:
        """ Returns a dict that contains the 'command' key with a system command to execute.
        May contain additional fields with arbitrary metadata.
        """
        full_request_url = f'{self.server_url}/distributed/get'
        auth_cookie = {'key': self.api_key}
        req = requests.get(full_request_url, cookies=auth_cookie, verify=self._verify_host)
        if req.status_code == 200:
            self.logger.debug(f"Got command from distributed queue: {req.json()}")
            return req.json()
        elif req.status_code == 304:
            return {}
        else:
            self.logger.error(f"HTTP Code received while getting distributed command: {req.status_code}")
            response = req.text
            self.logger.debug(response)
