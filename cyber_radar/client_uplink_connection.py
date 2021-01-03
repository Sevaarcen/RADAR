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
import requests
import re

from requests.exceptions import ConnectionError

import cyber_radar.constants as const

from cyber_radar.client_configuration_manager import ClientConfigurationManager


class UplinkConnection:
    def __init__(self):
        self.config = ClientConfigurationManager().config
        self.uplink_port = self.config.setdefault('uplink_port', 1684)
        self.url = f'http://{const.LOCAL_COMM_ADDR}:{self.uplink_port}'
        self._verify_connection()

    def _verify_connection(self):
        result = self.get_info()
        if not result:
            print("!!!  Connection to RADAR Uplink could not be established")
            exit(1)

    def get_info(self):
        endpoint = "/info/status"
        req = requests.get(f"{self.url}{endpoint}")
        if not req.ok:
            print(f"!!!  Uplink returned a non 200 status code: {req.status_code} {req.reason}")
            return False
        return req.text

    def get_mission_list(self):
        endpoint = "/mission/list"
        req = requests.get(f"{self.url}{endpoint}")
        if not req.ok:
            print(f"!!!  Uplink returned a non 200 status code: {req.status_code} {req.reason}")
            return False
        return req.json()

    def set_mission(self, new_mission: str):
        endpoint = "/mission/switch"
        if not re.match("^\w+$", new_mission):
            print("Invalid mission name")
            return False
        parameters = {
            "new_mission": new_mission
        }
        req = requests.post(f"{self.url}{endpoint}", params=parameters)
        if req.ok:
            print(req.text)
            return True
        elif req.status_code == 404:
            create_yn = input(f"The mission '{new_mission}' doesn't exist yet... create it? [Y/n]: ")
            if create_yn and create_yn.lower()[0] != 'y':
                print("User did not want to create a new mission")
                return False
            parameters["create"] = True
            req = requests.post(f"{self.url}{endpoint}", params=parameters)
            if req.ok:
                print(req.text)
                return True
            else:
                print(f"!!!  Uplink returned a non 200 status code: {req.status_code} {req.reason}")
                return False
        else:
            print(f"!!!  Uplink returned a non 200 status code: {req.status_code} {req.reason}")
            return False

    def get_key_authorization(self):
        endpoint = "/authorization/info"
        req = requests.get(f"{self.url}{endpoint}")
        if not req.ok:
            print(f"!!!  Uplink returned a non 200 status code: {req.status_code} {req.reason}")
            return False
        return req.text

    def change_key_authorization(self, api_key: str, superuser=False, authorizing=True):
        endpoint = "/authorization/modify"
        parameters = {
            "api_key": api_key,
            "superuser": superuser,
            "authorizing": authorizing
        }
        req = requests.post(f"{self.url}{endpoint}", params=parameters)
        if not req.ok:
            print(f"!!!  Uplink returned a non 200 status code: {req.status_code} {req.reason}")
            return False
        print(req.text)
        if authorizing:
            print(f"$$$  API key is now authorized (SU={superuser})")
        else:
            print("$$$  API key is now deauthorized")
        return True

    def get_database_structure(self):
        endpoint = "/database/info/structure"
        req = requests.get(f"{self.url}{endpoint}")
        if not req.ok:
            print(f"!!!  Uplink returned a non 200 status code: {req.status_code} {req.reason}")
            return False
        return req.json()

    def list_collections(self):
        endpoint = "/database/info/collections"
        req = requests.get(f"{self.url}{endpoint}")
        if not req.ok:
            print(f"!!!  Uplink returned a non 200 status code: {req.status_code} {req.reason}")
            return False
        return req.json()

    def send_data(self, collection: str, data: dict):
        endpoint = "/database/data/send"
        parameters =  {
            "collection": collection
        }
        req = requests.post(f"{self.url}{endpoint}", params=parameters, json=data)
        if not req.ok:
            print(f"!!!  Uplink returned a non 200 status code: {req.status_code} {req.reason}")
            return False
        return req.text

    def get_data(self, collection: str, database: str = None, query_filter: dict = None) -> dict:
        parameters =  {
            "collection": collection,
            "database": database
        }
        if not query_filter:
            endpoint = "/database/data/gather"
            req = requests.get(f"{self.url}{endpoint}", params=parameters)
        else:
            endpoint = "/database/data/query"
            req = requests.post(f"{self.url}{endpoint}", params=parameters, json=query_filter)
        if not req.ok:
            print(f"!!!  Uplink returned a non 200 status code: {req.status_code} {req.reason}")
            return None
        return req.json()
    
    def pop_share_data(self, query_filter: dict) -> dict:
        parameters = {
            "collection": const.DEFAULT_SHARE_COLLECTION
        }
        endpoint = ""
        endpoint = "/database/data/pop"
        req = requests.post(f"{self.url}{endpoint}", params=parameters, json=query_filter)
        if not req.ok:
            print(f"!!!  Uplink returned a non 200 status code: {req.status_code} {req.reason}")
            return None
        return req.json()

    def send_distributed_commands(self, command: list):
        endpoint = "/distributed/submit"
        req = requests.post(f"{self.url}{endpoint}", json=command)
        if not req.ok:
            print(f"!!!  Uplink returned a non 200 status code: {req.status_code} {req.reason} -- {req.text}")
            return None
        return req.text
