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
import yara
import importlib
from radar.objects import SystemCommand

DEFAULT_CONFIG = {
    "parser_rules": "parsing_rules.yara"
}


class CommandParserManager:

    def __init__(self):
        self.rule_path = DEFAULT_CONFIG['parser_rules']
        self.rules = yara.compile(self.rule_path)

    def _get_match_metadata(self, data):
        return

    def parse(self, command: SystemCommand):
        parse_results = {"RAW": command.to_json()}
        matches = self.rules.match(data=command.command_output, externals={"ext_command": command.command})
        for match in matches.get('main', {}):
            try:
                module_to_load = match.get('meta', {}).get('module')
                parser_module = importlib.import_module(f'radar.parsers.{module_to_load}')
                results = parser_module.run(command)
                parse_results.update({parser_module.MODULE_NAME: results})
            except ModuleNotFoundError as mnfe:
                print(f'!!!  Missing referenced parser: {mnfe}')
            except AttributeError as ae:
                print(f'!!!  Malformed parser: {ae}')
        return parse_results
