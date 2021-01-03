#!/usr/bin/python3
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
import pkgutil
import importlib
import json
import time
import netaddr
import re

import cyber_radar.playbooks
import cyber_radar.commanders

import cyber_radar.constants as const

from cyber_radar.client_uplink_connection import UplinkConnection


def get_info(uplink: UplinkConnection):
    info = uplink.get_info()
    print(info)


def distribute_command(uplink: UplinkConnection, distrib_command: str, extra_meta_args: list = []):
    syntax_pattern = '^(?P<targets>.+) ([iI][nN][tT][oO]) (?P<command>.*{}.*)$'
    parsed_command = re.search(syntax_pattern, distrib_command)
    
    if not parsed_command.group('targets'):
        print("!!!  Missing targets that go into distributed command")
        exit(1)
    if not parsed_command.group('command'):
        print("!!!  Missing distributed command with placeholder")
        exit(1)

    additional_meta = {}
    if extra_meta_args:
        for arg in extra_meta_args:
            key = arg.partition("=")[0]
            value = arg.partition("=")[0]
            if not key or not value:
                print("!!! Error with meta arg, must be in the 'key=metadata' format")
                exit(1)
            additional_meta[key] = value

    unprocessed_target_list = parsed_command.group('targets').split(',')
    target_list = []
    for target in unprocessed_target_list:
        target = target.strip()
        if len(target) > 0:
            target_list.append(target)

    command = parsed_command.group('command').strip()
    if len(target_list) == 0 or command == '':
        print('!!!  Either targets or command is missing content and is blank')
        exit(1)

    # tokenize each target in target_list
    print("###  Verifying targets")
    for target in target_list:
        if re.match(const.IPADDR_REX, target):
            print(f"  {target} is an IP address")
        elif re.match(const.IPRANGE_REX, target):
            print(f"  {target} is an IP range")
        elif re.match(const.IPCIDR_REX, target):
            print(f"  {target} is an CIDR network")
        else:
            print(f"  {target} is a hostname, URL, or other non-IP address target")
    valid = input("Does this look correct? [Y/n]: ").strip().lower()
    if len(valid) > 0 and valid[0] != 'y':
        print('!!!  You said targets are invalid... stopping now')
        exit(2)

    # Generate every single valid target
    all_targets = []
    for target in target_list:
        try:
            if re.match(const.IPADDR_REX, target):
                host_ip = netaddr.IPAddress(target)
                all_targets.append(str(host_ip))
            elif re.match(const.IPRANGE_REX, target):
                range_start_end = [ip.strip() for ip in target.split('-')]
                range_start = range_start_end[0]
                range_end = range_start_end[1]
                # check if end range is relative and we need to figure out start
                if range_start.count(".") > range_end.count("."):
                    relative_range_start = range_start.rsplit(".", range_end.count(".")+1)[0]
                    range_end = f"{relative_range_start}.{range_end}"
                iprange = netaddr.IPRange(range_start, range_end)
                for host_ip in iprange:
                    all_targets.append(str(host_ip))
            elif re.match(const.IPCIDR_REX, target):
                cidr = netaddr.IPNetwork(target)
                for host_ip in cidr.iter_hosts():
                    all_targets.append(str(host_ip))
            else:
                all_targets.append(target)
        except Exception as err:
            print(f"!!!  Invalid target '{target}': {err}")
    if len(all_targets) == 0:
        print("!!!  No valid targets... aborting")
        exit(1)

    print(f"$$$  A total of {len(all_targets)} targets were marked as valid")

    
    command_list = [{"command": command.replace('{}', target)} for target in all_targets]
    print(f"~~~  Example distirbuted command: '{command_list[0]}'")
    valid = input("Does this look correct? [Y/n]: ").strip().lower()
    if len(valid) > 0 and valid[0] != 'y':
        print('!!!  You said the command is wrong... stopping now')
        exit(2)
    
    # Add additional metadata to command
    if additional_meta:
        for command in command_list:
            command.update(additional_meta)

    print(f"$$$ Sending {len(command_list)} commands to be distributed")
    result = uplink.send_distributed_commands(command_list)
    if not result:
        print('!!!  Failed to send the commands to the Uplink')
    else:
        print(result)


def run_playbook(uplink: UplinkConnection, playbook: str, target: str, args: str):
    print(f'###  Manually executing playbook: {playbook} against {target}')
    manual_target = {'target_host': target, 'details': {'run_method': 'manual'}}
    for i in range(0, len(args)):
        manual_target[f'arg{i}'] = args[i]
    try:
        playbook_module = importlib.import_module(f'{const.PACKAGE_NAME}.playbooks.{playbook}')
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


def run_commander(uplink: UplinkConnection, commander: str, args=[]):
    print(f"###  Running AI commander: {commander}")
    try:
        commander_module = importlib.import_module(f"{const.PACKAGE_NAME}.commanders.{commander}")
        commander_module.run(uplink, args)
    except ModuleNotFoundError as mnfe:
        print(f'!!!  Missing referenced Commander: {mnfe}')
    except AttributeError as ae:
        print(f'!!!  Malformed Commander, missing required attribute: {ae}')
    except TypeError as te:
        print(f'!!!  Malformed Commander, the run method must take in the following args (uplink: UplinkConnection, args: list): {te}')
    except KeyboardInterrupt:
        print("!!!  Command cancelled by key interrupt")


def list_database_structure(uplink: UplinkConnection):
    structure = uplink.get_database_structure()
    for database_name, collection_list in structure.items():
        if database_name in const.PROTECTED_DATABASES:
            print(f'! {database_name}')
        elif database_name in const.RESTRICTED_DATABASES:
            print(f'# {database_name}')
        else:
            print(database_name)
        for collection in collection_list:
            print(f'--- {collection}')


def list_collections(uplink: UplinkConnection):
    collection_list = uplink.list_collections()
    for collection in collection_list.get("result", []):
        print(f"*  {collection}")


def read_database_contents(uplink: UplinkConnection, collection: str, database=None):
    contents = uplink.get_data(collection, database=database)
    print(json.dumps(contents, indent=4, sort_keys=True))


def list_missions(uplink: UplinkConnection):
    mission_list = uplink.get_mission_list()
    print("Available Missions w/ data")
    for mission in mission_list.get("result", []):
        print(f'> {mission}')


def join_mission(uplink: UplinkConnection, mission: str):
    uplink.set_mission(mission)


def check_auth(uplink: UplinkConnection):
    auth_status_string = uplink.get_key_authorization()
    print(auth_status_string)


def modify_auth(uplink: UplinkConnection, api_key: str, superuser=False, authorizing=True):
    uplink.change_key_authorization(api_key, superuser=superuser, authorizing=authorizing)


def document_commands(uplink: UplinkConnection, output_filename: str):
    """
    Prints a markdown-formatted document containing the commands, metadata, and output from all the current mission's commands
    """
    out_file = open(output_filename, "w")
    command_list = uplink.get_data(const.DEFAULT_COMMAND_COLLECTION)
    for item_number, command_data in enumerate(command_list):
        
        # Print header
        out_file.write(f"## Command number {item_number}\n\n")

        
        command = command_data.get("command")
        out_file.write(f"COMMAND $> {command}\n\n")
        
        working_dir = command_data.get("current_working_directory")
        out_file.write(f"Working Directory: {working_dir}\n\n")

        host = command_data.get("executed_on_host")
        out_file.write(f"Executed on Host: {host}\n\n")

        ipaddr = command_data.get("executed_on_ipaddr")
        out_file.write(f"Executed on IP: {ipaddr}\n\n")

        start_time_float = command_data.get("execution_time_start")
        start_time = time.strftime('%Y-%m-%d %H:%M:%S %z', time.localtime(start_time_float))
        out_file.write(f"Command Started at: {start_time}\n\n")

        end_time_float = command_data.get("execution_time_end")
        end_time = time.strftime('%Y-%m-%d %H:%M:%S %z', time.localtime(end_time_float))
        out_file.write(f"Command Finished at: {end_time}\n\n")

        return_code = command_data.get("command_return_code")
        out_file.write(f"Command returned exit code: {return_code}\n\n")
        
        output = command_data.get("command_output")
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
        distribute_command(uplink_connection, args.command, args.distrib_meta)
    elif command == "commander":
        run_commander(uplink_connection, args.commander, args.commander_args)
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
                                   help="Targets and command which will be executed " \
                                       "with a placeholder '{}' where the target(s) will get substituted separated by the 'into' keyword. " \
                                       "This could look like: " \
                                            "127.0.0.1, 192.168.1.0/24, 10.10.10.100-150, scanme.nmap.org INTO nmap {}")
    distribute_parser.add_argument("distrib_meta",
                                    type=str,
                                    nargs="*",
                                    default=[],
                                    help="key=value pairs of arbitrary metadata to include with command (e.g. 'job_number=1')")

    playbook_parser = subparsers.add_parser('playbook', help="Manually run playbook")
    valid_playbooks = [mod.name for mod in pkgutil.iter_modules(cyber_radar.playbooks.__path__)]
    playbook_parser.add_argument('-p',
                                 '--playbook',
                                 type=str,
                                 dest="playbook",
                                 required=True,
                                 help="Name of playbook",
                                 choices=valid_playbooks)
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
    
    commander_parser = subparsers.add_parser("commander", help="Run an AI commander")
    valid_commander_selections = [mod.name for mod in pkgutil.iter_modules(cyber_radar.commanders.__path__)]
    commander_parser.add_argument('commander',
                                  help="Which AI commander to execute",
                                  choices=valid_commander_selections)
    commander_parser.add_argument("commander_args",
                                 type=str,
                                 nargs="*",
                                 default=[],
                                 help="Any arguments to give to commander (passed as a list separated by spaces)")

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

    document_command_parser = subparsers.add_parser('document-commands', help="Create a file containing all commands " \
                                                                              "that were executed in the mission - " \
                                                                              "great for documentation")
    document_command_parser.add_argument('output_filename',
                                         type=str,
                                         help="Specify the filename to write the output to")

    arguments = parser.parse_args()

    dispatch(arguments.radar_command, args=arguments)
