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

import re

from typing import Tuple


# used if anything wants to sort/use numeric values instead of strings
VALUE_STANDARD_CONVERSIONS = {
    "unknown": 0,
    "low": 1,
    "medium": 2,
    "high": 3,
    "very-high": 4
}


# format
#   device_type_string
#       - list of services (if it might not appear in consistent ports) (THESE ARE REGULAR EXPRESSIONS!)
#       - list of ports that correspond to hosts of that type (prefered unless service tends to run on different ports)
HOST_TYPE = {
    "webserver": {
        "value": "high",
        "service_names": [
            "werkzeug",
            "httpd",
            "nginx",
            "apache"
        ],
        "ports": [
            80,
            443,
            3000,  # node webserver
            8000,
            8443
        ]
    },
    "database": {
        "value": "very-high",
        "service_names": [
        ],
        "ports": [
            1433,  # mssql
            3306,  # mysql
            6379,  # redis
            27017, # mongo
            
        ]
    },
    "fileserver": {
        "value": "high",
        "service_names": [
        ],
        "ports": [
            21,
            990
        ]
    },
    "mailserver": {
        "value": "medium",
        "service_names": [
        ],
        "ports": [
            25,  # smtp ports
            468,
            587,
            2525,
            110,  # pop3 ports
            993,
            143,  # imap ports
            995
        ]
    },
    "ics": {  # industrial control system
        "value": "very-high",
        "service_names": [
            "modbus"
        ],
        "ports": [
            502
        ]
    },
    "domain_controller": {
        "value": "very-high",
        "service_names": [
        ],
        "ports": [
            88  # kerberos
        ]
    }
}


def get_info(target: dict) -> Tuple[str, str]:
    """ For a given target, returns information about the priority and best-guess type of host

    arguments:
    target: a dictionary that conforms to RADAR target specifications

    returns:
    a tuple of strings (priority, type). First string is the value of the device (e.g. "high"), second is the type of device (e.g. "webserver").
    Multiple device types will be seperated with a semicolon (e.g. 'webserver;database').
    """
    services = target.get("services")

    if not services:  # no running services, we don't care
        return "unknown", "generic"
    
    device_value = "unknown"
    device_type = ""
    
    global HOST_TYPE
    global VALUE_STANDARD_CONVERSIONS
    # for every service on the target
    for service in services:
        port = int(service.get("port"))
        name = service.get("service")
        # check if any of the host types matches the target...
        for host_type, details in HOST_TYPE.items():
            # skip checking the type if it's already flagged (e.g. it has multiple services related to being a webserver)
            if host_type in device_type:
                continue
            type_value = details.get("value")
            # by seeing if the port is in one of the lists
            if port in details.get("ports"):
                device_value = device_value if VALUE_STANDARD_CONVERSIONS[type_value] < VALUE_STANDARD_CONVERSIONS[device_value] else type_value
                device_type += f";{host_type}"
            # or by seeing if any of the patterns matches
            else:
                for check_names in details.get("service_names", []):
                    if re.search(check_names, name):
                        device_value = device_value if VALUE_STANDARD_CONVERSIONS[type_value] < VALUE_STANDARD_CONVERSIONS[device_value] else type_value
                        device_type += f";{host_type}"
                        break
    
    return device_value, device_type[1:] or "unknown"
