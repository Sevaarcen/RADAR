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

from jsonrpcclient import request
from jsonrpcclient.exceptions import ReceivedNon2xxResponseError
from requests.exceptions import ConnectionError

from radar.client_configuration_manager import ClientConfigurationManager


class UplinkConnection:
    def __init__(self):
        self.config = ClientConfigurationManager().config
        self.uplink_port = self.config.setdefault('uplink_port', 1684)
        self.url = f'http://localhost:{self.uplink_port}'
        self._verify_connection()

    def _verify_connection(self):
        result = self.get_info()
        if not result:
            print("!!!  Connection to RADAR Uplink could not be established")
            exit(1)

    def get_info(self):
        rpc_method = "get_info"
        try:
            req = request(self.url, rpc_method)
            return req.data.result
        except (ReceivedNon2xxResponseError, ConnectionError):
            return False

    def get_mission_list(self):
        rpc_method = "get_mission_list"
        try:
            req = request(self.url, rpc_method)
            mission_list = req.data.result
            return mission_list
        except ReceivedNon2xxResponseError:
            return False

    def set_mission(self, new_mission: str):
        rpc_method = 'switch_mission'
        try:
            req = request(self.url, rpc_method, new_mission=new_mission)
            mission_list = req.data.result
            return mission_list
        except ReceivedNon2xxResponseError as err:
            if '400 status' in err:
                create_yn = input(f"The mission '{new_mission}' doesn't exist yet... create it? [Y/n]: ")
                try:
                    if create_yn.lower()[0] == 'y':
                        req = request(self.url, rpc_method, new_mission=new_mission, create=True)
                        print(req.data.result)
                    else:
                        return False
                except IndexError:
                    return False

    def get_key_authorization(self):
        rpc_method = 'is_authorized'
        try:
            req = request(self.url, rpc_method)
            return req.data.result
        except ReceivedNon2xxResponseError:
            return False

    def change_key_authorization(self, api_key: str, superuser=False, authorizing=True):
        rpc_method = 'modify_authorization'
        try:
            request(self.url, rpc_method, api_key=api_key, superuser=superuser, authorizing=authorizing)
            if authorizing:
                print(f"$$$  API key is now authorized (SU={superuser})")
            else:
                print("$$$  API key is now deauthorized")
            return True
        except ReceivedNon2xxResponseError:
            return False

    def get_database_structure(self):
        rpc_method = 'get_database_structure'
        try:
            req = request(self.url, rpc_method)
            return req.data.result
        except ReceivedNon2xxResponseError:
            return False

    def list_collections(self):
        rpc_method = 'get_collections'
        try:
            req = request(self.url, rpc_method)
            return req.data.result
        except ReceivedNon2xxResponseError:
            return False

    def send_data(self, collection: str, data: dict):
        rpc_method = 'send_data'
        try:
            request(self.url, rpc_method, collection=collection, data=data)
            return True
        except ReceivedNon2xxResponseError:
            return False

    def get_data(self, collection, database=None):
        rpc_method = 'get_data'
        try:
            req = request(self.url, rpc_method, collection=collection, database=database)
            return req.data.result
        except ReceivedNon2xxResponseError:
            return False

    def send_distributed_commands(self, command: list):
        rpc_method = 'send_distributed_commands'
        try:
            request(self.url, rpc_method, command=command)
            return True
        except ReceivedNon2xxResponseError as err:
            raise err
            return False
