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

import cyber_radar.constants as const

from cyber_radar.system_command import SystemCommand
from cyber_radar.client_configuration_manager import ClientConfigurationManager


class CommandParserManager:

    def __init__(self):
        client_config_manager = ClientConfigurationManager()
        client_config = client_config_manager.config
        self.rule_path = client_config['rules']['parser_rules']
        try:
            self.rules = yara.compile(self.rule_path)
        except yara.Error:
            print(f"!!!  Could not load parsing rules with file path: '{self.rule_path}'")
            exit(1)

        self.current_command = None
        self.metadata_results_buffer = None
        self.target_results_buffer = None
    
    def yara_callback(self, match_data):
        try:
            module_to_load = match_data.get('meta', {}).get('module', None)
            if not module_to_load:
                print(f'!!!  No parser module specified for parser rule {match_data.get("rule")}')
            else:
                parser_module = importlib.import_module(f'{const.PACKAGE_NAME}.parsers.{module_to_load}')
                metadata, target_data = parser_module.run(self.current_command)
                self.metadata_results_buffer.update({module_to_load: metadata})
                for target in target_data:  # Make sure each target says where it came from
                    target['source_command'] = self.current_command.uuid
                self.target_results_buffer += target_data
        except ModuleNotFoundError as mnfe:
            print(f'!!!  Missing referenced parser: {mnfe}')
        except AttributeError as ae:
            print(f'!!!  Malformed parser, missing required attribute: {ae}')
        except TypeError as te:
            print(f'!!!  Malformed parser, the run method must take in a "CommandOutput" object: {te}')

    def parse(self, command: SystemCommand):
        """ Takes the SystemCommand and runs it through the parsers as defined in the parsing rules (yara file).
        :param command: SystemCommand that was exectured
        :return: Two JSON dictionaries - metadata and target data
        """
        self.current_command = command
        self.metadata_results_buffer = {"SOURCE_UUID": command.uuid, "RAW_COMMAND": command.to_json()}
        self.target_results_buffer = []
        matches = self.rules.match(data=command.command_output, externals={"ext_command": command.command}, callback=self.yara_callback, which_callbacks=yara.CALLBACK_MATCHES)
        return self.metadata_results_buffer, self.target_results_buffer


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
        client_config_manager = ClientConfigurationManager()
        client_config = client_config_manager.config
        self.rule_path = client_config['rules']['playbook_rules']
        try:
            self.rules = yara.compile(self.rule_path)
        except yara.Error:
            print(f"!!!  Could not load playbook rules with file path: '{self.rule_path}'")
            exit(1)

        self.current_target_dict = None
        self.current_skip_list = None
        self.current_silent = None
    
    def yara_callback(self, match_data):
        try:
            module_to_load = match_data.get('meta', {}).get('module', None)
            if not module_to_load:
                print(f'!!!  No playbook specified for playbook rule {match_data.get("rule")}')
            elif module_to_load not in self.current_skip_list:
                playbook_module = importlib.import_module(f'{const.PACKAGE_NAME}.playbooks.{module_to_load}')
                results = playbook_module.run(self.current_target_dict)
                if results and not self.current_silent:
                    print(results)
                self.current_skip_list.append(module_to_load)  # Don't rerun the same Playbook, prevent infinite loop
                self.rules.match(data=self.flat_current_target_data_string, callback=self.yara_callback, which_callbacks=yara.CALLBACK_MATCHES)  # Recursive
                return  # Ensure only 1 module is executed per iteration of this method
        except ModuleNotFoundError as mnfe:
            print(f'!!!  Missing referenced Playbook: {mnfe}')
        except AttributeError as ae:
            print(f'!!!  Malformed Playbook, missing required attribute: {ae}')
        except TypeError as te:
            print(f'!!!  Malformed Playbook, the run method must take in the target as a dict: {te}')
    
    def automate(self, target_list: list, skip_list=[], silent=False):
        self.current_silent = silent
        self.current_skip_list = skip_list
        for target in target_list:
            self.current_target_dict = target
            if not isinstance(target, dict):
                print(f"!!!  While running playbook, target wasn't a valid JSON dict: {target}")
                continue
            # Pull out variables so it's easier to reference
            self.flat_current_target_data_string = _flatten_to_string(target)
            self.rules.match(data=self.flat_current_target_data_string, callback=self.yara_callback, which_callbacks=yara.CALLBACK_MATCHES)