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

import time

import pandas as pd


def target_list_to_dataframe(targets: list) -> pd.DataFrame:
    """Returns a Pandas DataFrame containing the target details. This DataFrame conforms to the Pennsylvania State University's
    Competitive Cyber Security Organization (CCSO) 'Target Tracking Spreadsheet' format at https://ccso.psu.edu/penetration-testing-resources/.

    Args:
        targets (list): List of dicts of RADAR target details

    Returns:
        pd.DataFrame: DataFrame of target details conforming to template at https://ccso.psu.edu/penetration-testing-resources/.
    """
    # Create blank dataframe we are going to fill with values
    df_index = [target.get("target_host") for target in targets]
    df = pd.DataFrame(index=df_index)
    
    
    # metadata so we can pull data from RADAR if wanted
    df['radar_command_uuid'] = [target.get("source_command") for target in targets]
    df['scan_time'] = [time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime(target.get("details", {}).get("scan_time"))) for target in targets]
    
    # Details about host
    df['IP/Hostname'] = [target.get("target_host") for target in targets]
    df['Host Type'] = [target.get("details", {}).get("host_type") for target in targets]
    df['Level of Interest'] = [target.get("details", {}).get("value") for target in targets]
    df['Level of Access'] = ["None" for _ in targets]  # Placeholder, this will be filled in later manually by user
    df["Notes"] = ""
    
    # Now add ports to spreadsheet
    added_cols = []
    for target in targets:
        indx = target.get("target_host")
        for service in target.get("services", []):
            name = f"{service.get('port')}/{service.get('protocol')}"
            # If column is not in dataframe yet, add it
            if name not in added_cols:
                added_cols.append(name)
                df[name] = ""
            cell_value = service.get("version") or service.get("service") or service.get("state") or "MISSING"
            df.at[indx, name] = cell_value
            
    return df
