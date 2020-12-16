import pkg_resources
import argparse

parser = argparse.ArgumentParser()
parser.add_argument('-c',
                    '--config',
                    dest='config_path',
                    type=str,
                    help="Specify non-default configuration file to use")
arguments = parser.parse_args()

config_filepath = arguments.config_path
print(config_filepath)
if not config_filepath:
    config_filepath = "config/test.toml"
print(pkg_resources.resource_filename(__name__, config_filepath))
print(pkg_resources.resource_filename(pkg_resources.Requirement.parse("cyber_radar"), config_filepath))
