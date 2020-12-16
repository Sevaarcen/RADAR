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

import setuptools


with open("README.md", "r", encoding="utf-8") as readme_fh:
    long_description = readme_fh.read()

with open("requirements.txt", "r", encoding="utf-8") as requirements_fh:
    required_packages = requirements_fh.read().splitlines()


# executable scripts to install
scripts = [
    "scripts/radar.py",
    "scripts/radar-ctl.py",
    "scripts/radar-uplink.py",
    "scripts/radar-server.py",
]

# extra non-package files that should be installed w/ package
data_files = [
    "config/client_config.toml",
    "config/uplink_config.toml",
    "config/server_config.toml",
    "LICENSE",
    "README.md",
    "USER GUIDE.md",
]

setuptools.setup(
    name="cyber-radar",
    version="0.1.1",
    author="Cole Daubenspeck",
    description="A framework to support a Red-team Analysis, Documentation, and Automation Revolution!",
    long_description=long_description,
    long_description_content_type="text/markdown",
    license="GPLv3",
    url="https://github.com/sevaarcen/RADAR",
    packages=setuptools.find_packages(),
    scripts=scripts,
    data_files=data_files,
    # tags and stuff for project
    classifiers=[
        "Programming Language :: Python :: 3",
        "Operating System :: OS Independent",
        "Development Status :: 4 - Beta",
    ],
    # gotta have 3.6+ for the f-strings :)
    python_requires='>=3.6',
    # other things required for this to be installed correctly
    install_requires=required_packages
)
