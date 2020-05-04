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

# Useful reference: https://www.blackhillsinfosec.com/password-spraying-other-fun-with-rpcclient/

import os
import re
import shutil

from radar.system_command import SystemCommand

def run(target: dict):
    # Check to ensure rpcinfo is installed
    rpcclient_exists = shutil.which('rpcclient')
    if not rpcclient_exists:
        return f'!!!  MSRPC enumeration failed, RPCClient not installed'
    
    target_host = target.get('target_host', None)
    if not target_host:
        return f'!!!  MSRPC enumeration failed, no target_host specified: {target}'
    
    rpcclient_cmd_format = f'''rpcclient -U "" -N {target_host} -c '%s' ''' # Command format
    
    #============================================================
    #  Check if host is vulnerable
    #============================================================
    check_anon_cmd = SystemCommand(rpcclient_cmd_format % 'getusername')
    check_anon_cmd.run()

    target_details = target.setdefault('details', {})

    if 'NT_STATUS_ACCESS_DENIED' in check_anon_cmd.command_output.split('\n'):
        target_details['anonymous-smb'] = False
        return f'!!!  MSRPC enumeration failed, permission denied on {target_host}'
    
    # Else, run all enumerations
    target.setdefault('vulnerabilities', []).append('anonymous-smb')
    

    #============================================================
    #  Gather password requirements
    #============================================================
    get_pw_requirements_cmd = SystemCommand(rpcclient_cmd_format % 'getdompwinfo')
    get_pw_requirements_cmd.run()

    password_requirements_dict = {}
    for line in get_pw_requirements_cmd.command_output.split('\n'):
        split_line = line.partition(':')
        field_name = split_line[0].strip()
        field_value = split_line[2].strip()
        password_requirements_dict[field_name] = field_value
    
    target_details['password-requirements'] = password_requirements_dict

    #============================================================
    #  Gather user info
    #============================================================
    get_user_list_cmd = SystemCommand(rpcclient_cmd_format % 'enumdomusers')
    get_user_list_cmd.run()

    # Grab list of valid user ID's (rid)
    user_rid_list = []
    for line in get_user_list_cmd.command_output.split('\n'):
        regex = r'user:\[(?P<username>.*?)\] rid:\[(?P<rid>.*?)\]'
        matches = re.search(regex, line)
        if not matches:
            continue

        rid = matches.group('rid').strip()
        user_rid_list.append(rid)
    
    # Query each RID for detailed info
    # collect into list
    detailed_user_info = []
    for rid in user_rid_list:
        get_user_details_cmd = SystemCommand(rpcclient_cmd_format % f'queryuser {rid}')
        get_user_details_cmd.run()

        user_info_dict = {}
        for line in get_user_details_cmd.command_output.split('\n'):
            split_line = line.partition(':')
            field_name = split_line[0].strip()
            field_value = split_line[2].strip()
            user_info_dict[field_name] = field_value
        detailed_user_info.append(user_info_dict)
    
    target_details['user-info'] = detailed_user_info

    #============================================================
    #  Gather detailed group info
    #============================================================
    get_group_list_cmd = SystemCommand(rpcclient_cmd_format % 'enumdomgroups')
    get_group_list_cmd.run()

    # Grab list of valid group ID's (rid)
    group_rid_list = []
    for line in get_user_list_cmd.command_output.split('\n'):
        regex = r'group:\[(?P<group_name>.*?)\] rid:\[(?P<rid>.*?)\]'
        matches = re.search(regex, line)
        if not matches:
            continue

        rid = matches.group('rid').strip()
        group_rid_list.append(rid)
    
    # Join group RID w/ detailed info about it
    detailed_group_info = []
    for rid in group_rid_list:
        get_group_details_cmd = SystemCommand(rpcclient_cmd_format % f'querygroup {rid}')
        get_group_details_cmd.run()

        group_info_dict = {'rid': rid}  # This field isn't in detailed info, adding beforehand
        for line in get_user_details_cmd.command_output.split('\n'):
            split_line = line.partition(':')
            field_name = split_line[0].strip()
            field_value = split_line[2].strip()
            group_info_dict[field_name] = field_value
        detailed_group_info.append(group_info_dict)
    
    target_details['group-info'] = detailed_group_info

    # TODO add even more enumeration, maybe members of each group (make sure to prevent recursion)

    return f'$$$  MSRPC enumeration completed on {target_host}'

