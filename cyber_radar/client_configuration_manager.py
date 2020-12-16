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

import cyber_radar.constants as const
import toml


def verify_config(config: dict) -> bool:
    critical_error = False
    rules = config.get("rules", None)
    if not rules:
        print("!!!  Client configuration file is missing 'rules' section")
        critical_error = True
    else:
        parser_rules = rules.get("parser_rules", None)
        if not parser_rules:
            print("!!!  Client configuration missing 'parser_rules' in 'rules' section")
            critical_error = True
        playbook_rules = rules.get("playbook_rules", None)
        if not playbook_rules:
            print("!!!  Client configuration missing 'playbook_rules' in 'rules' section")
            critical_error = True
    return not critical_error


class ClientConfigurationManager:
    class __ClientConfigurationManager:
        def __init__(self, config_path):
            self.config_path = config_path
            try:
                self.config = toml.load(self.config_path)
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
