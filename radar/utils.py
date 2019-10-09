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
    if radar_command == 'server':
        print(f"Connected to server at: {server_connection}")

    elif radar_command == 'art':
        print_art()

    elif radar_command == 'db_list':
        if not radar_command_arguments:
            print('!!!  You must specify a database and collection. Usage: radar db_list <database> <collection>')
            return
        collection = radar_command_arguments
        server_connection.list_database_contents(collection)

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
