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

# For client/server database controls
MISSION_PREFIX = "mission-"
DEFAULT_MISSION = "default"
DEFAULT_COMMAND_COLLECTION = 'raw-commands'
DEFAULT_METADATA_COLLECTION = 'command_metadata'
DEFAULT_TARGET_COLLECTION = 'targets'

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
