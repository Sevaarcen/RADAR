#!/bin/bash
if [ `id -u` != 0 ]
then
  echo "This script must be run as root, or using 'sudo'"
  exit 1
fi

echo "Determining package manager to use..."
if [[ $(which apt-get) ]]; then
    pmgr="apt-get"
elif [[ $(which yum) ]]; then
    pmgr="yum"
elif [[ $(which dnf) ]]; then
    pmgr="dnf"
else
    echo "Unable to determine package manager to use... aborting"
    exit 1
fi


echo "Package manager is: '$pmgr'"

sudo $pmgr install -y python3-pip yara samba-common