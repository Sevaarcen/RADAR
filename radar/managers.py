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
        """ Takes the SystemCommand and runs it through the parsers as defined in the parsing rules (yara file).
        :param command: SystemCommand that was exectured
        :return: Two JSON dictionaries - metadata and target data
        """
        metadata_results = {"RAW_COMMAND": command.to_json()}
        target_results = {}
        matches = self.rules.match(data=command.command_output, externals={"ext_command": command.command})
        for match in matches.get('main', {}):
            try:
                module_to_load = match.get('meta', {}).get('module', None)
                if not module_to_load:
                    print(f'!!!  No parser module specified for parser rule {match.get("rule")}')
                else:
                    parser_module = importlib.import_module(f'radar.parsers.{module_to_load}')
                    metadata, target_data = parser_module.run(command)
                    metadata_results.update({parser_module.MODULE_NAME: metadata})
                    target_results.update(target_data)
            except ModuleNotFoundError as mnfe:
                print(f'!!!  Missing referenced parser: {mnfe}')
            except AttributeError as ae:
                print(f'!!!  Malformed parser, you must have a "run" method: {ae}')
            except TypeError as te:
                print(f'!!!  Malformed parser, the run method must take in a "CommandOutput" object: {te}')
        return metadata_results, target_results
