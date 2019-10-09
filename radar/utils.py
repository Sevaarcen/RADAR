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
from radar.objects import *


def run_radar_command(command: str, server_connection: ServerConnection):
    """ Process an internal radar command, possibly interacting with the server
    :param command: The RADAR command to be executed
    :param server_connection: The ServerConnection object
    :return: None
    """
    command_split = command.split(' ', 2)
    if len(command_split) < 2:
        print('!!!  No RADAR command specified')
        return
    radar_command = command_split[1]
    radar_command_arguments = command_split[2] if len(command_split) > 2 else None

    # Process each command
    if radar_command == 'help':
        print("""
RADAR COMMANDS:
server                                  (print the address you're connected to)
mission_info                            (print info about the current mission)
mission_list                            (list all missions that contain data)
mission_join <name>                     (create/join a different mission)
collection_list                         (list all collections in your current mission)
collection_read <collection>            (list the data in the specified collection)
mongo_list                              (lists the structure of the Mongo database)
mongo_read <database> <collection>      (print the data from the specific database and collection)
request_auth                            (send a request to authorize with the server)
check_auth                              (print your authorization level)
""")
    elif radar_command == 'server':
        print(f"Connected to server at: {server_connection}")

    elif radar_command == 'art':
        print_art()

    elif radar_command == 'mission_info':
        print(f"$$$  You're currently joined to: {server_connection.mission}")

    elif radar_command == 'mission_list':
        mission_list = server_connection.get_mission_list()
        for mission in mission_list:
            print(f'*  {mission}')

    elif radar_command == 'mission_join':
        mission_list = server_connection.get_mission_list()
        if any(radar_command_arguments == mission for mission in mission_list):
            server_connection.mission = radar_command_arguments
            print(f"###  You have joined the mission: {server_connection.mission}")
        else:
            create_yn = input("This mission doesn't exist yet... create it? (Y/n): ")
            try:
                if create_yn.lower()[0] == 'y':
                    server_connection.mission = radar_command_arguments
                    print(f"###  You have joined the mission: {server_connection.mission}")
            except IndexError:
                pass

    elif radar_command == 'collection_list':
        collection_list = server_connection.get_collection_list()
        for collection_name in collection_list:
            print(collection_name)

    elif radar_command == 'collection_read':
        if not radar_command_arguments:
            print('!!!  You must specify a collection in the current database')
            return
        collection = radar_command_arguments
        server_connection.list_database_contents(collection)

    elif radar_command == 'mongo_list':
        database_structure = server_connection.get_mongo_structure()
        print(json.dumps(database_structure, indent=4, sort_keys=True))

    elif radar_command == 'mongo_read':
        if not radar_command_arguments:
            print('!!!  You must specify a database and collection')
            return
        split_args = radar_command_arguments.split(' ')
        if len(split_args) != 2:
            print('!!!  You must specify a database and collection')
            return
        database = split_args[0]
        collection = split_args[1]
        server_connection.list_database_contents(collection, database=database)

    elif radar_command == 'request_auth':
        print('###  Requesting authorization...')
        server_connection.request_authorization()

    elif radar_command == 'check_auth':
        result = server_connection.get_authorization()
        if result[1]:
            print('You are authorized as a superuser!')
        elif result[0]:
            print('You are authorized.')
        else:
            print('You are unauthorized, please ask a superuser to authorize you...')

    else:
        print(f'!!!  Unknown radar command: {radar_command}')
        run_radar_command('radar help', server_connection)


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
