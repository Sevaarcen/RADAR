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
import importlib

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
        run_radar_command('radar help', server_connection)
        return
    radar_command = command_split[1]
    radar_command_arguments = command_split[2] if len(command_split) > 2 else None

    # Process each command
    if radar_command == 'help':
        print("""
RADAR COMMANDS:
server                                      (print the address you're connected to)
playbook <playbook_name> <target> (args)    (manually run a playbook on the target. args are added to the target dict)
mission_info                                (print info about the current mission)
mission_list                                (list all missions that contain data)
mission_join <name>                         (create/join a different mission)
collection_list                             (list all collections in your current mission)
collection_read <collection>                (list the data in the specified collection)
mongo_list                                  (lists the structure of the Mongo database)
mongo_read <database> <collection>          (print the data from the specific database and collection)
check_auth                                  (print your authorization level)
request_auth                                (send a request to authorize with the server)
grant_auth <username> (superuser)           (send a request to grant the user authorization)
remove_auth <username>                      (remove authorization from client given username)
""")
    elif radar_command == 'server':
        print(f"Connected to server at: {server_connection}")

    elif radar_command == 'art':
        print_art()

    elif radar_command == 'playbook':
        if not radar_command_arguments:
            print('!!!  No arguments given for running a manual playbook')
            return
        else:
            playbook_args = radar_command_arguments.split(' ')
            if len(playbook_args) < 2:
                print('!!!  Invalid number of arguments for running a manual playbook')
                return
            playbook_name = playbook_args[0]
            target_host = playbook_args[1]
            args = playbook_args[2:]
            run_playbook(playbook_name, target_host, args)

    elif radar_command == 'mission_info':
        print(f"$$$  You're currently joined to: {server_connection.mission}")

    elif radar_command == 'mission_list':
        mission_list = server_connection.get_mission_list()
        for mission in mission_list:
            print(f'*  {mission}')

    elif radar_command == 'mission_join':
        mission_input = radar_command_arguments.strip()
        if len(mission_input) == 0:
            print(f"###  Invalid request, returning to the mission: {server_connection.mission}")
            return
        mission_list = server_connection.get_mission_list()
        if any(mission_input == mission for mission in mission_list):
            server_connection.mission = mission_input
            print(f"###  You have joined the mission: {server_connection.mission}")
        else:
            create_yn = input(f"The mission '{mission_input}' doesn't exist yet... create it? [Y/n]: ")
            try:
                if create_yn.lower()[0] == 'y':
                    server_connection.mission = radar_command_arguments
                    print(f"###  You have joined the mission: {server_connection.mission}")
                else:
                    print(f"Request cancelled, you're joined to the mission '{server_connection.mission}'")
                    print("Use the command: 'radar mission_join <mission_name>' the change missions later")
            except IndexError:
                server_connection.mission = radar_command_arguments
                print(f"###  You have joined the mission: {server_connection.mission}")

    elif radar_command == 'collection_list':
        collection_list = server_connection.get_collection_list()
        for collection_name in collection_list:
            print(collection_name)

    elif radar_command == 'collection_read':
        if not radar_command_arguments:
            print('!!!  You must specify a collection in the current database')
            return
        collection = radar_command_arguments
        results = server_connection.get_database_contents(collection)
        if results:
            print(json.dumps(results, indent=4, sort_keys=True))

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
        results = server_connection.get_database_contents(collection, database=database)
        if results:
            print(json.dumps(results, indent=4, sort_keys=True))

    elif radar_command == 'check_auth':
        result = server_connection.get_authorization()
        if result[1]:
            print('You are authorized as a superuser!')
        elif result[0]:
            print('You are authorized.')
        else:
            print('You are unauthorized, please ask a superuser to authorize you...')

    elif radar_command == 'request_auth':
        print('###  Requesting authorization...')
        server_connection.request_authorization()

    elif radar_command == 'grant_auth':
        split_args = radar_command_arguments.split(' ') if radar_command_arguments else []
        if len(split_args) < 1:
            print('!!!  You must specify a username')
            return
        superuser = False
        try:
            if 'true' in split_args[1].lower() or 'y' in split_args[1][0].lower() or 'su' in split_args[1]:
                superuser = True
        except IndexError:
            pass
        server_connection.modify_authorization(split_args[0], superuser=superuser, authorizing=True)

    elif radar_command == 'remove_auth':
        if not radar_command_arguments:
            print('!!!  You must specify a username')
            return
        server_connection.modify_authorization(radar_command_arguments.strip(), authorizing=False)

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


def run_playbook(playbook: str, target_host: str, args: list):
    print(f'###  Manually executing playbook: {playbook}')
    manual_target = {'target_host': target_host}
    for i in range(0, len(args)):
        manual_target[f'arg{i}'] = args[i]
    try:
        playbook_module = importlib.import_module(f'radar.playbooks.{playbook}')
        playbook_module.run(manual_target)
    except ModuleNotFoundError as mnfe:
        print(f'!!!  Missing referenced Playbook: {mnfe}')
    except AttributeError as ae:
        print(f'!!!  Malformed Playbook, missing required attribute: {ae}')
    except TypeError as te:
        print(f'!!!  Malformed Playbook, the run method must take in the target as a dict: {te}')
    except KeyboardInterrupt:
        print("!!!  Command cancelled by key interrupt")
