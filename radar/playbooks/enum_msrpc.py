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
    
    base_format = f'''rpcclient -U "" -N {target_host} -c '%s' ''' # Command format
    
    # Check if we *can* enumerate the host
    check_anon_cmd = SystemCommand(base_format % 'getusername')
    check_anon_cmd.run()

    if 'NT_STATUS_ACCESS_DENIED' in check_anon_cmd.command_output:
        target_details = target.setdefault('details', {})
        target_details['anonymous-smb'] = False
        return f'!!!  MSRPC enumeration failed, permission denied on {target_host}'
    
    # Else, run all enumerations
    target.setdefault('vulnerabilities', []).append('anonymous-smb')
    return f'$$$  MSRPC enumeration completed on {target_host}'
    get_pw_requirements_cmd = SystemCommand(base_format % 'getdompwinfo')
    get_pw_requirements_cmd.run()

