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

from ftplib import FTP, error_perm


def run(target: dict):
    target_host = target.get('target_host', None)
    if not target_host:
        return f'!!!  Scan Anonymous FTP failed, no target_host specified: {target}'
    try:
        ftp_connection = FTP(target_host)
        ftp_connection.login()  # Login anonymous

        target_vulns = target.get('vulnerabilities', None)
        if target_vulns:
            target_vulns.append('Anonymous FTP Login')
        else:
            target['vulnerabilities'] = ['Anonymous FTP Login']

        return f'$$$  {target_host} is vulnerable to Anonymous FTP Login'
    except (ConnectionRefusedError, error_perm):
        return
