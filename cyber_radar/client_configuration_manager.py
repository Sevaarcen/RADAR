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

import pkg_resources
import toml

import cyber_radar.constants as const


def verify_config(config: dict) -> bool:
    # get value or set to default filepath if not valid
    rules = config.setdefault("rules", {})
    rules.setdefault("parser_rules", pkg_resources.resource_filename(__name__, const.PARSER_RULES))
    rules.setdefault("playbook_rules", pkg_resources.resource_filename(__name__, const.PLAYBOOK_RULES))


class ClientConfigurationManager:
    class __ClientConfigurationManager:
        def __init__(self, config_path):
            self.config_path = config_path
            try:
                self.config = toml.load(self.config_path)
                verify_config(self.config)
            except FileNotFoundError:
                print(f"!!!  Could not find configuration file: {config_path}")
                exit(1)

    instance = None

    def __new__(cls, config_path=None):
        if not ClientConfigurationManager.instance:
            if not config_path:
                # get default config file based on package install location
                import pkg_resources
                config_path = pkg_resources.resource_filename(const.PACKAGE_NAME, const.CLIENT_CONFIG)
            ClientConfigurationManager.instance = ClientConfigurationManager.__ClientConfigurationManager(config_path)
        return ClientConfigurationManager.instance

    def __getattr__(self, item):
        return getattr(self.instance, item)

    def __setattr__(self, key, value):
        return setattr(self.instance, key, value)
