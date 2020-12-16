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

from ftplib import FTP


def run(target: dict):
    target_host = target.get('target_host', None)
    if not target_host:
        return f'!!!  FTP directory listing failed, no target_host specified: {target}'
    ftp_connection = FTP(target_host)
    ftp_connection.login()
    files = ftp_connection.nlst()

    # Add info to metadata
    if not target.get('details', None):
        target['details'] = {}
    target['details']['ftp_server_contents'] = files
    return f'$$$  These files/directories were on the anonymous FTP server: {files}'

