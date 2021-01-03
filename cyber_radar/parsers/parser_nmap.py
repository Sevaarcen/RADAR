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

import time
import re

import cyber_radar.helpers.target_prioritizer as target_prioritizer

from cyber_radar.system_command import SystemCommand


def run(command: SystemCommand):
    target_list = []
    parse_results = {'targets': target_list}
    nmap_output = command.command_output.split('\n')
    for line in nmap_output:
        try:
            line = line.strip()
            if len(line) == 0:
                continue
            elif 'scan report for' in line:
                current_target = line.split(' ')[4]
                target_list.append({'target_host': current_target, "services": [], 'details': {}})

            elif 'Host is' in line:
                split_line = line.split(' ')
                target_list[len(target_list)-1]['details']['status'] = split_line[2]
                target_list[len(target_list)-1]['details']['latency'] = split_line[3][1:-1]

            elif '/tcp' in line or '/udp' in line:
                regex = '^(?P<port>[0-9]+)/(?P<protocol>[a-z]+)\s+(?P<state>.*?)(\s+(?P<service>.*?))?(\s+(?P<version>.*))?$'
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
                version = matches.group('version')
                if version:
                    info['version'] = version
                target_list[len(target_list)-1]['services'].append(info)

            elif 'Network Distance' in line:
                hop_number = line.split(' ')[1]
                target_list[len(target_list)-1]['details']['hop_distance'] = hop_number

            elif 'MAC Address' in line:
                try:
                    split_line = line.split(':', 1)
                    address_and_vendor = split_line[1].strip()
                    split_addr_and_vendor = address_and_vendor.split(' ', 1)
                    mac_addr = split_addr_and_vendor[0]
                    vendor = split_addr_and_vendor[1][1:-1]
                    target_list[len(target_list)-1]['details']['mac_address'] = mac_addr
                    target_list[len(target_list)-1]['details']['mac_address_vendor'] = vendor
                except IndexError:
                    continue

            elif 'Nmap done' in line:
                regex = '^Nmap done: (?P<total_scanned>[0-9]+) IP address(es)? ' \
                        '\((?P<total_online>[0-9]+).*?scanned in (?P<scan_duration>[0-9\.]+ .*)$'
                matches = re.search(regex, line)
                if not matches:
                    continue
                parse_results['total_scanned'] = matches.group('total_scanned')
                parse_results['total_online'] = matches.group('total_online')
                parse_results['scan_duration'] = matches.group('scan_duration')

        except IndexError as ie:
            print(f"!!! Error parsing NMAP, index error: {ie}")
            continue

    # Use target prioritizer helper module to get high-level info about type of device and expected value
    for target in target_list:
        host_value, host_type = target_prioritizer.get_info(target)
        target.setdefault('details', {}).update({
            "value": host_value,
            "host_type": host_type
        })
    # and finally... insert current timestamp for when data was parsed
    for target in target_list:
        target.setdefault('details', {})["scan_time"] = int(time.time())
    # Return parsing results and list of valid targets
    return parse_results, target_list
