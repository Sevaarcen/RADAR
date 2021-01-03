#!/bin/bash
if [ `id -u` != 0 ]; then
  echo "This script must be run as root, or using 'sudo'"
  exit 1
fi

echo "Determining package manager to use..."
if [ -n "$(which apt)" ]; then
    pmgr="apt"
elif [ -n "$(which yum)" ]; then
    pmgr="yum"
elif [ -n "$(which dnf)" ]; then
    pmgr="dnf"
else
    echo "Unable to determine package manager to use... aborting"
    exit 1
fi


echo "Package manager is: '$pmgr'"

required_packages=(
    "python3",
    "yara"
    "samba-common"
)
echo "Installing required packages: ${required_packages[@]}"
sudo $pmgr install -y "${required_packages[@]}"