import pkg_resources
import argparse

parser = argparse.ArgumentParser()
parser.add_argument('-c',
                    '--config',
                    dest='config_path',
                    type=str,
                    help="Specify non-default configuration file to use")
arguments = parser.parse_args()
print(arguments.config_path)
print(pkg_resources.resource_filename(pkg_resources.Requirement.parse("cyber_radar"), arguments.config_path))