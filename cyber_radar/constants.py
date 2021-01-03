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

# package info / distribution-related stuff
PACKAGE_NAME = "cyber_radar"

# Config files
CLIENT_CONFIG = "config/client_config.toml"
UPLINK_CONFIG = "config/uplink_config.toml"
SERVER_CONFIG = "config/server_config.toml"

# default rule filepaths
PARSER_RULES = "rules/parsing_rules.yara"
PLAYBOOK_RULES = "rules/playbook_rules.yara"

# Helpful regexes for working with target info
IPADDR_REX = '^([0-9]{1,3}\.){3}[0-9]{1,3}$'
IPRANGE_REX = '^([0-9]{1,3}\.){3}[0-9]{1,3} *\- *([0-9]{1,3}\.){0,3}[0-9]{1,3}$'
IPCIDR_REX = '^([0-9]{1,3}\.){3}[0-9]{1,3}/[0-9]{1,2}$'

# For client/server database controls
MISSION_PREFIX = "mission-"
DEFAULT_MISSION = "default"
DEFAULT_COMMAND_COLLECTION = 'raw-commands'
DEFAULT_METADATA_COLLECTION = 'command-metadata'
DEFAULT_TARGET_COLLECTION = 'targets'
DEFAULT_SHARE_COLLECTION = 'shared-data'

# Databases which the API shouldn't access
PROTECTED_DATABASES = [
    'admin',
    'config',
    'local'
]
# Databases which should only be accessed by superusers
RESTRICTED_DATABASES = [
    'radar-control'
]

# Uplink <--> client settings for communication optimization
LOCAL_COMM_ADDR = "127.0.0.1"

# For Uplink safety
UPLINK_API_KEY_FILENAME = "uplink_api_key.txt"
UPLINK_SAVED_QUEUE_FILENAME = "uplink_queue.txt"
