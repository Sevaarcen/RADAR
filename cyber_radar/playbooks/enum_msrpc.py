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

from cyber_radar.system_command import SystemCommand

rpcclient_cmd_format = ""

def run(target: dict):
    # Check to ensure rpcinfo is installed
    rpcclient_exists = shutil.which('rpcclient')
    if not rpcclient_exists:
        return f'!!!  MSRPC enumeration failed, RPCClient not installed'
    
    target_host = target.get('target_host', None)
    if not target_host:
        return f'!!!  MSRPC enumeration failed, no target_host specified: {target}'
    
    global rpcclient_cmd_format
    rpcclient_cmd_format = f'''rpcclient -U "" -N {target_host} -c '%s' ''' # Command format
    
    #============================================================
    #  Check if host is vulnerable
    #============================================================
    check_anon_cmd = SystemCommand(rpcclient_cmd_format % 'getusername')
    check_anon_cmd.run()

    target_details = target.setdefault('details', {})

    if 'NT_STATUS_ACCESS_DENIED' in check_anon_cmd.command_output:
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
        if field_value != "":
            continue
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
        user_info_dict = query_user_info(rid)
        user_info_dict['data-source'] = 'msrpc'
        detailed_user_info.append(user_info_dict)
    
    target_details['user-info'] = detailed_user_info

    #============================================================
    #  Gather detailed group info
    #============================================================
    get_group_list_cmd = SystemCommand(rpcclient_cmd_format % 'enumdomgroups')
    get_group_list_cmd.run()

    # Grab list of valid group ID's (rid)
    group_rid_list = []
    for line in get_group_list_cmd.command_output.split('\n'):
        regex = r'group:\[(?P<group_name>.*?)\] rid:\[(?P<rid>.*?)\]'
        matches = re.search(regex, line)
        if not matches:
            continue
        rid = matches.group('rid').strip()
        group_rid_list.append(rid)
    
    # Join group RID w/ detailed info about it
    detailed_group_info = []
    for rid in group_rid_list:
        
        group_info_dict = query_group_info(rid)
        group_info_dict['data-source'] = 'msrpc'

        # Then get members of group so it's easy to view.
        #print(f"GETTING MEMBERS OF {rid}")
        get_group_members_cmd = SystemCommand(rpcclient_cmd_format % f'querygroupmem {rid}')
        get_group_members_cmd.run()

        # Get list of group's members
        group_member_list = []
        for line in get_group_members_cmd.command_output.split('\n'):
            regex = r'rid:\[(?P<member_rid>.*?)\] attr:\[(?P<attr>.*?)\]'
            matches = re.search(regex, line)
            if not matches:
                continue
            # Get basic info about members
            member_rid = matches.group('member_rid')
            #print(f"member rid found: {member_rid}")
            attr = matches.group('attr')
            group_member_info_dict = {
                'user_rid': member_rid,
                'attr': attr
            }
            # Join with username field for ease-of-use
            member_username = None
            if member_rid in user_rid_list:  # Already enumerated
                for userinfo in detailed_user_info:
                    if member_rid == userinfo.get('user_rid', None):
                        member_username = userinfo.get('User Name')
                        #print(f"matched known user: {member_username}")
                        break
            else:  # It's an unknown user
                #print("DID NOT MATCH KNOWN USER")
                # Query info
                unknown_member_info = query_user_info(member_rid) 
                # Add info to existing lists
                user_rid_list.append(member_rid)
                detailed_user_info.append(unknown_member_info)
                # Then add the field of interest
                member_username = unknown_member_info.get('User Name')
                #print(f"member is: {member_username}")
            group_member_info_dict['User Name'] = member_username
            group_member_list.append(group_member_info_dict)  # Append info to list

        group_info_dict['member-info'] = group_member_list  # Add list to group dict
        detailed_group_info.append(group_info_dict)  # Add all group info to master list

    target_details['group-info'] = detailed_group_info  # Add group metadata to target details

    return f'$$$  MSRPC enumeration completed on {target_host}'


def query_user_info(rid: str) -> dict:
    #print(f"USER RID: {rid}")
    get_user_details_cmd = SystemCommand(rpcclient_cmd_format % f'queryuser {rid}')
    get_user_details_cmd.run()

    # If permission denied when querying user
    if 'NT_STATUS_ACCESS_DENIED' in get_user_details_cmd.command_output:
        #print(f"permission denied when quering user rid: {rid}")
        return {'user_rid': rid, 'error-message': get_user_details_cmd.command_output}

    user_info_dict = {}
    for line in get_user_details_cmd.command_output.split('\n'):
        #print(line)
        split_line = line.partition(':')
        field_name = split_line[0].strip()
        field_value = split_line[2].strip()
        if field_value == '':  # Ignore non-KV lines
            continue
        user_info_dict[field_name] = field_value
    return user_info_dict


def query_group_info(rid: str) -> dict:
    #print(f"GROUP RID: {rid}")
    get_group_details_cmd = SystemCommand(rpcclient_cmd_format % f'querygroup {rid}')
    get_group_details_cmd.run()

    # If permission denied when querying group
    if 'NT_STATUS_ACCESS_DENIED' in get_group_details_cmd.command_output:
        #print(f"permission denied when quering group rid: {rid}")
        return {'group_rid': rid, 'error-message': get_group_details_cmd.command_output}

    group_info_dict = {'group_rid': rid}  # This field isn't in detailed info, adding beforehand
    for line in get_group_details_cmd.command_output.split('\n'):
        #print(line)
        split_line = line.partition(':')
        field_name = split_line[0].strip()
        field_value = split_line[2].strip()
        if field_value == '':  # Ignore non-KV lines
            continue
        group_info_dict[field_name] = field_value
    return group_info_dict