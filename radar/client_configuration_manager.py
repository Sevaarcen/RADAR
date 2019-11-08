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
import toml


def verify_config(config: dict) -> bool:
    critical_error = False
    server = config.get("server", None)
    if not server:
        print("!!!  Client configuration file is missing 'server' section")
        critical_error = True
    else:
        server_host = server.get("host", None)
        if not server_host:
            print("!!!  Client configuration missing 'host' in 'server' section")
            critical_error = True
        server_port = server.get('port', None)
        if not server_port:
            print("!!!  Client configuration missing 'port' in 'server' section, assuming default")
        server_try_https = server.get('attempt-https', None)
        if server_try_https is None:
            print("!!!  Client configuration missing 'attempt-https' in 'server' section, assuming True")

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

    def __new__(cls, config_path="client_config.toml"):
        if not ClientConfigurationManager.instance:
            ClientConfigurationManager.instance = ClientConfigurationManager.__ClientConfigurationManager(config_path)
        return ClientConfigurationManager.instance

    def __getattr__(self, item):
        return getattr(self.instance, item)

    def __setattr__(self, key, value):
        return setattr(self.instance, key, value)
