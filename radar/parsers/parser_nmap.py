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
from radar.objects import SystemCommand
import re

MODULE_NAME = "PARSE_NMAP"


def run(command: SystemCommand,):
    parse_results = {}
    nmap_output = command.command_output.split('\n')
    current_target = None
    for line in nmap_output:
        line = line.strip()
        print(line)
        if 'scan report for' in line:
            current_target = line.split(' ')[4]
            parse_results[current_target] = {"services": [], 'details': {}}
        elif 'Host is' in line:
            split_line = line.split(' ')
            parse_results[current_target]['status'] = split_line[2]
            parse_results[current_target]['latency'] = split_line[3][1:-1]
        elif '/tcp' or '/udp' in line:
            regex = '^(?P<port>[0-9]+)/(?P<protocol>[a-z]+)\s+(?P<state>.*?)(\s+(?P<service>.*))?$'
            matches = re.search(regex, line)
            if not matches:
                continue
            info = {}
            port = matches.group('port')
            info['port'] = port
            protocol = matches.group('protocol')
            info['protocol'] = protocol
            state = matches.group('state')
            info['state'] = state
            service = matches.group('service')
            if service:
                info['service'] = service
            parse_results[current_target]['services'].append(info)
        elif 'Network Distance' in line:
            hop_number = line.split(' ')[1]
            parse_results[current_target]['details']['hop_distance'] = hop_number
        elif 'MAC Address' in line:
            split_line = line.split(' ')
            mac_addr = split_line[1]
            parse_results[current_target]['details']['mac_address'] = mac_addr
            if len(split_line) > 2:
                vendor = split_line[2]
                parse_results[current_target]['details']['mac_address_vendor'] = vendor

    return parse_results
