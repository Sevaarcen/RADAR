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
import sys
import requests
import json
import base64
import getpass
from radar.objects import SystemCommand


def run_radar_command(command, server_url):
    """ Process an internal radar command, possibly interacting with the server
    :param command: The RADAR command to be executed
    :param server_url: The RADAR Control Server the client is using
    :return: None
    """
    command_split = command.split(' ', 2)
    if len(command_split) < 2:
        print('!!!  No RADAR command specified')
        return
    radar_command = command_split[1]
    radar_command_arguments = command_split[2] if len(command_split) > 2 else None

    # Process each command
    if radar_command == 'server':
        print(f"Connected to server at: {server_url}")

    elif radar_command == 'art':
        print_art()

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
        print(f'!!!  Unknown radar command: {radar_command}')


def is_server_online(server_url):
    """ Connects to the server and checks the HTTP status code
    :param server_url: The RADAR Control Server
    :return: True if the status code is 200, else False
    """
    full_request_url = f'{server_url}/'
    request = requests.get(full_request_url)
    return request.status_code == 200


def get_authorization(server_url):
    """ Returns information about the client's authorization level
    :param server_url: The RADAR Control Server
    :return: A tuple containing two booleans - is_authorized and is_superuser
    """
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
    """ Sends a request to authorize the client based on their current username
    :param server_url: The RADAR Control Server
    :return: None
    """
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
def send_raw_command_output(server_url, command):
    """ Send the command and command results to the server to be inserted into the Mongo database
    :param server_url: The RADAR Control Server
    :param command: The SystemCommand object to sync
    :return: None
    """
    json_data = command.to_json()
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
    """ List the contents of one of the database collections from the server in JSON
    :param server_url: The RADAR Control Server
    :param database: The name of the database
    :param collection: The name of the collection
    :return: None
    """
    full_list_url = f'{server_url}/database/{database}/{collection}/list'
    request = requests.get(full_list_url)
    if request.status_code != 200:
        print(f"!!!  HTTP Code: {request.status_code}")
        response = request.text
        print(response)
    else:
        response = request.json()
        print(json.dumps(response, indent=4, sort_keys=True))


def print_art():
    """ Prints out ASCII art...
    :return: None
    """
    print('''
                           ,,ggddY""""Ybbgg,,
                     ,agd""'               `""bg,
                  ,gdP"             █     /   "Ybg,
                ,dP"        ▓            /       "Yb,
              ,dP"         _,,ddP"""Ybb,,_         "Yb,
             ,8"         ,dP"'         `"Yb,         "8,
            ,8'   ▒    ,d"            /    "b,        `8,
           ,8'        d"  ▓          /       "b        `8,
           d'        d'        ,gPPRg,        `b        `b
           8   ▒     8        dP'  /`Yb        8         8
           8         8    ▒   8)  *  (8        8         8
           8         8        Yb     dP        8         8
           8         Y,        "8ggg8"        ,P         8
           Y,   ░     Ya                     aP         ,P
           `8,         "Ya   ░             aP"         ,8'
            `8,          "Yb,_         _,dP"          ,8'
             `8a           `""YbbgggddP""'           a8'
              `Yba                                 adP'
                "Yba           ░                 adY"
                  `"Yba,                     ,adP"'
                     `"Y8ba,             ,ad8P"'
                          ``""YYbaaadPP""''
            ''')
