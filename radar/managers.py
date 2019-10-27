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
    "parser_rules": "parsing_rules.yara",
    "playbook_rules": "playbook_rules.yara"
}


class CommandParserManager:

    def __init__(self):
        self.rule_path = DEFAULT_CONFIG['parser_rules']
        self.rules = yara.compile(self.rule_path)

    def parse(self, command: SystemCommand):
        """ Takes the SystemCommand and runs it through the parsers as defined in the parsing rules (yara file).
        :param command: SystemCommand that was exectured
        :return: Two JSON dictionaries - metadata and target data
        """
        metadata_results = {"RAW_COMMAND": command.to_json()}
        target_results = []
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
                    target_results += target_data
            except ModuleNotFoundError as mnfe:
                print(f'!!!  Missing referenced parser: {mnfe}')
            except AttributeError as ae:
                print(f'!!!  Malformed parser, missing required attribute: {ae}')
            except TypeError as te:
                print(f'!!!  Malformed parser, the run method must take in a "CommandOutput" object: {te}')
        return metadata_results, target_results


def _flatten(to_flatten, parent_key=""):
    if isinstance(to_flatten, list):
        results = {}
        for i in range(0, len(to_flatten)):
            results.update(_flatten(to_flatten[i], parent_key=f'{parent_key}[{i}]'))
        return results
    elif isinstance(to_flatten, dict):
        results = {}
        for key, value in to_flatten.items():
            new_key = f'{parent_key}.{key}' if parent_key != "" else key
            results.update(_flatten(value, parent_key=new_key))
        return results
    else:
        return {parent_key: to_flatten}


def _flatten_to_string(to_flatten):
    flattened = _flatten(to_flatten)
    result = ""
    for key, value in flattened.items():
        result += f'{key} = {value}\n'
    return result.strip()


class PlaybookManager:

    def __init__(self):
        self.rule_path = DEFAULT_CONFIG['playbook_rules']
        self.rules = yara.compile(self.rule_path)

    def automate(self, target_list: list):
        for target in target_list:
            if not isinstance(target, dict):
                print(f"!!!  While running playbook, target wasn't a valid JSON dict: {target}")
                continue
            # Pull out variables so it's easier to reference
            target_as_string = _flatten_to_string(target)
            if 'target_host' not in target_as_string or 'services' not in target_as_string:
                print("!!!  Invalid target format, it doesn't conform to the specifications. Skipping...")
                print(target)
                continue
            matches = self.rules.match(data=target_as_string)
            for match in matches.get('main', {}):
                try:
                    module_to_load = match.get('meta', {}).get('module', None)
                    if not module_to_load:
                        print(f'!!!  No playbook specified for playbook rule {match.get("rule")}')
                    else:
                        playbook_module = importlib.import_module(f'radar.playbooks.{module_to_load}')
                        playbook_module.run(target)
                except ModuleNotFoundError as mnfe:
                    print(f'!!!  Missing referenced Playbook: {mnfe}')
                except AttributeError as ae:
                    print(f'!!!  Malformed Playbook, missing required attribute: {ae}')
                except TypeError as te:
                    print(f'!!!  Malformed Playbook, the run method must take in the target as a dict: {te}')
