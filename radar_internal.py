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

import argparse
import importlib
import json
import time

from radar.client_uplink_connection import UplinkConnection
import radar.constants as const


def get_info(uplink: UplinkConnection):
    info = uplink.get_info()
    print(info)


def distribute_command(uplink: UplinkConnection, command: str):
    uplink.send_distributed_command(command)


def run_playbook(uplink: UplinkConnection, playbook: str, target: str, args: str):
    print(f'###  Manually executing playbook: {playbook} against {target}')
    manual_target = {'target_host': target, 'details': {'run_method': 'manual'}}
    for i in range(0, len(args)):
        manual_target[f'arg{i}'] = args[i]
    try:
        playbook_module = importlib.import_module(f'radar.playbooks.{playbook}')
        results = playbook_module.run(manual_target)
        print(results)
    except ModuleNotFoundError as mnfe:
        print(f'!!!  Missing referenced Playbook: {mnfe}')
    except AttributeError as ae:
        print(f'!!!  Malformed Playbook, missing required attribute: {ae}')
    except TypeError as te:
        print(f'!!!  Malformed Playbook, the run method must take in the target as a dict: {te}')
    except KeyboardInterrupt:
        print("!!!  Command cancelled by key interrupt")
    uplink.send_data(const.DEFAULT_TARGET_COLLECTION, manual_target)


def list_database_structure(uplink: UplinkConnection):
    structure = uplink.get_database_structure()
    for database_name, collection_list in structure.items():
        print(database_name)
        for collection in collection_list:
            print(f'> {collection}')


def list_collections(uplink: UplinkConnection):
    collection_list = uplink.list_collections()
    for collection in collection_list:
        print(collection)


def read_database_contents(uplink: UplinkConnection, collection: str, database=None):
    contents = uplink.get_data(collection, database=database)
    print(json.dumps(contents, indent=4, sort_keys=True))


def list_missions(uplink: UplinkConnection):
    mission_list = uplink.get_mission_list()
    print("Available Missions w/ data")
    for mission in mission_list:
        print(f'> {mission}')


def join_mission(uplink: UplinkConnection, mission: str):
    uplink.set_mission(mission)


def check_auth(uplink: UplinkConnection):
    uplink.get_key_authorization()


def modify_auth(uplink: UplinkConnection, api_key: str, superuser=False, authorizing=True):
    uplink.change_key_authorization(api_key, superuser=superuser, authorizing=authorizing)


def document_commands(uplink: UplinkConnection, output_filename: str):
    out_file = open(output_filename, "w")
    command_list = uplink.get_data(const.DEFAULT_COMMAND_COLLECTION)
    for command_data in command_list:
        start_time_float = command_data.get("execution_time_start")
        start_time = time.strftime('%Y-%m-%d %H:%M:%S %z', time.localtime(start_time_float))
        end_time_float = command_data.get("execution_time_end")
        end_time = time.strftime('%Y-%m-%d %H:%M:%S %z', time.localtime(end_time_float))
        host = command_data.get("executed_on_host")
        command = command_data.get("command")
        output = command_data.get("command_output")

        out_file.write(f"RADAR COMMAND EXECUTION $> {command}\n")
        out_file.write(f"Executed on Host: {host}\n")
        out_file.write(f"Command Started at: {start_time}\n")
        out_file.write(f"Command Finished at: {end_time}\n")
        out_file.write("OUTPUT:\n")
        out_file.write("```\n")
        for line in output.split("\n")[:-1]:
            out_file.write(f'{line.strip()}\n')
        out_file.write("```\n")
        out_file.write("\n\n\n")


def dispatch(command: str, args=None):
    uplink_connection = UplinkConnection()
    if command == 'info':
        get_info(uplink_connection)
    elif command == 'distribute':
        distributed_command = args.command
        distribute_command(uplink_connection, distributed_command)
    elif command == 'playbook':
        run_playbook(uplink_connection, args.playbook, args.target, args.playbook_args)
    elif command == 'collection-list':
        list_collections(uplink_connection)
    elif command == 'database-list':
        list_database_structure(uplink_connection)
    elif command == 'get-data':
        collection = args.collection
        database = args.database
        read_database_contents(uplink_connection, collection, database=database)
    elif command == 'mission-list':
        list_missions(uplink_connection)
    elif command == 'mission-join':
        join_mission(uplink_connection, args.mission)
    elif command == 'check-auth':
        check_auth(uplink_connection)
    elif command == 'grant-auth':
        modify_auth(uplink_connection, args.api_key, superuser=args.superuser)
    elif command == 'remove-auth':
        modify_auth(uplink_connection, args.api_key, authorizing=False)
    elif command == 'document-commands':
        output_filename = args.output_filename
        document_commands(uplink_connection, output_filename)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(prog="RADAR Internal Command Client")
    subparsers = parser.add_subparsers(help='Valid commands', required=True, dest="radar_command")

    info_parser = subparsers.add_parser('info', help="Get info about RADAR's state")

    distribute_parser = subparsers.add_parser('distribute', help="Run command on first available client")
    distribute_parser.add_argument('command',
                                   type=str,
                                   help="Command which will be executed")

    playbook_parser = subparsers.add_parser('playbook', help="Manually run playbook")
    playbook_parser.add_argument('-p',
                                 '--playbook',
                                 type=str,
                                 dest="playbook",
                                 required=True,
                                 help="Name of playbook")
    playbook_parser.add_argument('-t',
                                 '--target',
                                 type=str,
                                 dest="target",
                                 required=True,
                                 help="Target of playbook")
    playbook_parser.add_argument("playbook_args",
                                 type=str,
                                 nargs="*",
                                 default=[],
                                 help="All arguments in a single string (separated by spaces)")

    list_collection_parser = subparsers.add_parser('collection-list', help="List available collections")

    list_database_parser = subparsers.add_parser('database-list', help="List all databases and collections")

    get_data_parser = subparsers.add_parser('get-data', help="Read from any database and collection")
    get_data_parser.add_argument('-c',
                                 '--collection',
                                 type=str,
                                 dest="collection",
                                 required=True,
                                 help="Which collection to read")
    get_data_parser.add_argument('-d',
                                 '--database',
                                 type=str,
                                 dest="database",
                                 required=False,
                                 help="Which database to read")

    mission_list_parser = subparsers.add_parser('mission-list', help="List missions which have data")

    mission_join_parser = subparsers.add_parser('mission-join', help="Change to another mission")
    mission_join_parser.add_argument('mission',
                                     type=str,
                                     help="Name of mission")

    check_auth_parser = subparsers.add_parser('check-auth', help="Print authorization info")

    change_auth_parser = subparsers.add_parser('grant-auth', help="Grant an API key authorization")
    change_auth_parser.add_argument('api_key',
                                    type=str,
                                    help="API Key to change authorization of")
    change_auth_parser.add_argument('--superuser',
                                    action="store_true",
                                    dest="superuser",
                                    help="Make the user a superuser")

    remove_auth_parser = subparsers.add_parser('remove-auth', help="Remove an API key's authorization")
    remove_auth_parser.add_argument('api_key',
                                    type=str,
                                    help="API Key to change authorization of")

    document_command_parser = subparsers.add_parser('document-commands', help="Create a file containing all commands" \
                                                                              "that were executed in the mission - " \
                                                                              "great for documentation")
    document_command_parser.add_argument('output_filename',
                                         type=str,
                                         help="Specify the filename to write the output to")

    arguments = parser.parse_args()

    dispatch(arguments.radar_command, args=arguments)
