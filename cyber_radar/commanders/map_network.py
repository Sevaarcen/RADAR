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

import netaddr
import re
import os
import uuid
import time
import json

from tqdm import tqdm

import cyber_radar.constants as const
import cyber_radar.helpers.target_formatter as target_formatter

from cyber_radar.client_configuration_manager import ClientConfigurationManager
from cyber_radar.client_uplink_connection import UplinkConnection


DEFAULT_SCAN_TIMING = 4
FAST_TOP_PORT_NUMBER = "500"  # Number of top ports to scan to find valid targets
UDP_TOP_PORTS_COUNT = "500"  # Number of top UDP ports to scan for valid targets

POLL_INTERVAL = ClientConfigurationManager().config.get("commander_poll_interval", 15)


def run(uplink: UplinkConnection, args: list):
    #===============================================================================
    #  Double check that's everything is valid and there won't be issues running this
    #===============================================================================
    if not args:
        print("!!!  No targets specified - list all target IP addresses, IP ranges, CIDR, or hostnames to include in scope as arguments to this commander")
        exit(1)
    
    # Ensure we have the correct auth level to prevent useless work and wasted time
    auth_info_string = uplink.get_key_authorization()
    if auth_info_string and "SU=True" not in auth_info_string:
        print("!!!  You lack superuser authorization which is required for this commander...")
        exit(3)

    # Generate UUID to ensure multiple commander executions don't conflict
    commander_uuid = str(f"map_network_{uuid.uuid4()}")

    print(f"###  The commander's UUID is: {commander_uuid}")

    output_dir = os.path.join(os.path.expanduser("~"), commander_uuid)
    print(f"###  Commander will save output files to: '{output_dir}'")

    # tokenize each target in target_list
    print("###  Verifying targets")
    for target in args:
        if re.match(const.IPADDR_REX, target):
            print(f"  {target} is an IP address")
        elif re.match(const.IPRANGE_REX, target):
            print(f"  {target} is an IP range")
        elif re.match(const.IPCIDR_REX, target):
            print(f"  {target} is an CIDR network")
        else:
            print(f"  {target} is a hostname, URL, or other non-IP address target")
    valid = input("Does everything look correct? [Y/n]: ").strip().lower()
    if len(valid) > 0 and valid[0] != 'y':
        print('!!!  You said targets are invalid... stopping now')
        exit(2)
    
    # Create directory for where output will be saved
    os.mkdir(output_dir)

    # Tokenize targets into a list that contains all possible targets within specified scope(s)
    all_targets = []
    for target in args:
        try:
            if re.match(const.IPADDR_REX, target):
                host_ip = netaddr.IPAddress(target)
                all_targets.append(str(host_ip))
            elif re.match(const.IPRANGE_REX, target):
                range_start_end = [ip.strip() for ip in target.split('-')]
                range_start = range_start_end[0]
                range_end = range_start_end[1]
                # check if end range is relative and we need to figure out start
                if range_start.count(".") > range_end.count("."):
                    relative_range_start = range_start.rsplit(".", range_end.count(".")+1)[0]
                    range_end = f"{relative_range_start}.{range_end}"
                iprange = netaddr.IPRange(range_start, range_end)
                for host_ip in iprange:
                    all_targets.append(str(host_ip))
            elif re.match(const.IPCIDR_REX, target):
                cidr = netaddr.IPNetwork(target)
                for host_ip in cidr.iter_hosts():
                    all_targets.append(str(host_ip))
            else:
                all_targets.append(target)
        except Exception as err:
            print(f"!!!  Invalid target '{target}': {err}")
    
    all_target_count = len(all_targets)
    if all_target_count == 0:
        print("!!!  No valid targets... aborting")
        exit(1)
    
    print("="*80)
    #===============================================================================
    #  run fast scan for quick info on all targets
    #===============================================================================
    host_identification_command_list = []
    global DEFAULT_SCAN_TIMING
    global FAST_TOP_PORT_NUMBER
    host_identification_command = f"nmap TARGET -T{DEFAULT_SCAN_TIMING} --top-ports {FAST_TOP_PORT_NUMBER}"
    for num, target in enumerate(all_targets):
        command = host_identification_command.replace("TARGET", target)
        command_dict = {
            "command": command,
            "commander_source": commander_uuid,
            "job_number": num,
            "request_share": True
        }
        host_identification_command_list.append(command_dict)
    
    # distribute fast scan commands
    print(f"###  Performing a quick scan using {all_target_count} distributed commands")
    uplink.send_distributed_commands(host_identification_command_list)

    # poll share list until all commands are finished
    print(f"###  {all_target_count} distributed commands sent, waiting for completion")
    global POLL_INTERVAL
    
    
    gathered_target_data = []
    # While this is running, use a fancy loading bar that shows progress
    pbar = tqdm(desc="Running distributed quick network map", total=all_target_count)
    outstanding_jobs = list(range(all_target_count))
    distrib_command_meta = []

    while len(outstanding_jobs) > 0:
        time.sleep(POLL_INTERVAL)
        new_metadata = uplink.pop_share_data({"commander_source": commander_uuid})
        # If there's more data to process, do so
        if new_metadata:
            pbar.update(len(new_metadata))  # Relative, so add count of new metadata
            # Add to list of all metadata collected
            distrib_command_meta += new_metadata
            tqdm.write(f"{len(new_metadata)} new commands have finished since last poll... processing now")

            # Mark job ID as complete
            oldest_job_number = outstanding_jobs[0]
            to_pull = []
            for job in new_metadata:
                job_number = job.get("job_number")
                # Ensure it's not a duplicate (maybe if commander believed job was stuck)
                if job_number not in outstanding_jobs:
                    continue
                outstanding_jobs.remove(job_number)
                to_pull.append(job.get("pull_command_uuid"))

            # Check if there's any stuck jobs that should be re-distributed
            if outstanding_jobs and oldest_job_number == outstanding_jobs[0]:  # Oldest hasn't been completed and is still the oldest
                tqdm.write(f"Job {oldest_job_number} may be stuck - distribute manually if it is - '{host_identification_command_list[oldest_job_number]}'")
                tqdm.write(f"Remaining jobs:  {outstanding_jobs}")

            # Pull back details on every valid target
            target_details_query = {"source_command": {"$in": to_pull}}
            gathered_target_data += uplink.get_data(const.DEFAULT_TARGET_COLLECTION, query_filter=target_details_query)
    pbar.close()
    # END OF PROGRESS BAR

    # Dump meta at the end
    dcommand_meta_filepath = os.path.join(output_dir, "fast_distrib_meta.json")
    tqdm.write(f"###  Saving distributed command metadata to: '{dcommand_meta_filepath}'")
    with open(dcommand_meta_filepath, "w") as fh:
        json.dump(distrib_command_meta, fh, indent=4)

    # all jobs are done and it's time to process results
    num_valid_targets = len(gathered_target_data)
    print(f"$$$  Fast scan complete: {num_valid_targets} hosts are valid targets out of the {all_target_count} tested")

    # Ensure there is actual targets to do an intense scan on
    if num_valid_targets == 0:
        print("!!!  No hosts were identified as online in the given scopes, aborting...")
        exit(0)
    
    # Dump files to save path as backup and for ease of use
    fscan_result_path = os.path.join(output_dir, "fast_scan_results.json")
    print(f"###  Saving fast scan results to: '{fscan_result_path}'")
    with open(fscan_result_path, "w") as fh:
        json.dump(gathered_target_data, fh, indent=4)
    
    print("="*80)

    #===============================================================================
    #  Perform an TCP all-ports scan of the identified hosts to identify all services
    #===============================================================================
    print(f"$$$  Performing an intense scan of the {num_valid_targets} online targets")
    identified_targets = [target.get("target_host") for target in gathered_target_data]

    intense_scan_command_list = []
    intense_tcp_scan_commandstr = f"nmap TARGET -T{DEFAULT_SCAN_TIMING} -p 1-65535 -sV -Pn"
    for num, target in enumerate(identified_targets):
        command = intense_tcp_scan_commandstr.replace("TARGET", target)
        command_dict = {
            "command": command,
            "commander_source": commander_uuid,
            "job_number": num,
            "request_share": True
        }
        intense_scan_command_list.append(command_dict)
    
    # distribute fast scan commands
    print(f"###  Performing intense network scans using {num_valid_targets} distributed commands")
    uplink.send_distributed_commands(intense_scan_command_list)

    # poll share list until all commands are finished
    print(f"###  {num_valid_targets} distributed commands sent, waiting for completion")

    # Use slower poll interval because we expect these commands to take significaly longer
    intense_poll_interval = 4 * POLL_INTERVAL
    
    intense_tcp_port_scan_results = []
    # Once again, use a fancy progress bar
    pbar = tqdm(desc="Running intense TCP port scan of identified targets", total=num_valid_targets)
    outstanding_jobs = list(range(num_valid_targets))
    distrib_command_meta = []

    while len(outstanding_jobs) > 0:
        time.sleep(intense_poll_interval)
        new_metadata = uplink.pop_share_data({"commander_source": commander_uuid})
        # If there's more data to process, do so
        if new_metadata:
            # Add to list of all metadata collected
            pbar.update(len(new_metadata))  # Relative, so add count of new metadata
            distrib_command_meta += new_metadata
            tqdm.write(f"{len(new_metadata)} new commands have finished since last poll... processing now")

            # Mark job ID as complete
            oldest_job_number = outstanding_jobs[0]
            to_pull = []
            for job in new_metadata:
                job_number = job.get("job_number")
                # Ensure it's not a duplicate (maybe if commander believed job was stuck)
                if job_number not in outstanding_jobs:
                    continue
                outstanding_jobs.remove(job_number)
                to_pull.append(job.get("pull_command_uuid"))

            # Check if there's any stuck jobs that should be re-distributed
            if outstanding_jobs and oldest_job_number == outstanding_jobs[0]:  # Oldest hasn't been completed and is still the oldest
                tqdm.write(f"Job {oldest_job_number} may be stuck - distribute manually if it is - '{intense_scan_command_list[oldest_job_number]}'")
                tqdm.write(f"Remaining jobs:  {outstanding_jobs}")

            # Pull back details on every valid target
            target_details_query = {"source_command": {"$in": to_pull}}
            new_scan_results = uplink.get_data(const.DEFAULT_TARGET_COLLECTION, query_filter=target_details_query)
            for new_target in new_scan_results:
                host = new_target.get('target_host')
                host_value = new_target.get("details", {}).get("value")
                host_type = new_target.get("details", {}).get("host_type")
                tqdm.write(f"$$$  '{host}' identified as a '{host_type}' device of '{host_value}' value")
                identified_vulns = new_target.get("vulnerabilities")
                if identified_vulns:
                    tqdm.write(f"$!$  RADAR identified the following vulnerabilities on '{host}': {identified_vulns}")
            intense_tcp_port_scan_results += new_scan_results
    # Dump meta at the end
    dcommand_meta_filepath = os.path.join(output_dir, "intense_tcp_distrib_meta.json")
    tqdm.write(f"###  Saving TCP scan distributed command metadata to: '{dcommand_meta_filepath}'")
    with open(dcommand_meta_filepath, "w") as fh:
        json.dump(distrib_command_meta, fh, indent=4)
    pbar.close()
    # END OF PROGRESS BAR
    
    # Dump files to output location
    intense_tcp_result_path = os.path.join(output_dir, "intense_tcp_port_scan.json")
    print(f"###  Saving tcp scan results to: '{intense_tcp_result_path}'")
    with open(intense_tcp_result_path, "w") as fh:
        json.dump(intense_tcp_port_scan_results, fh, indent=4)
    
    dataframe_csv_path = os.path.join(output_dir, "target_details_tcponly.csv")
    print(f"###  Formatting target details to CSV and saving results to: '{dataframe_csv_path}'")
    target_dataframe = target_formatter.target_list_to_dataframe(intense_tcp_port_scan_results)
    target_dataframe.to_csv(dataframe_csv_path, index=False)
    
    # Also print out to console
    print("="*35 + " TCP PORT SCAN RESULTS " + "="*35)
    print(json.dumps(intense_tcp_port_scan_results, indent=4))
    print("="*80)

    #===============================================================================
    #  Run UDP port scan for some common ports just to make sure we don't miss anything
    #===============================================================================
    print(f"$$$  Performing a UDP scan of the {num_valid_targets} online targets")

    udp_scan_command_list = []
    udp_scan_commandstr = f"nmap TARGET -T{DEFAULT_SCAN_TIMING} --top-ports {UDP_TOP_PORTS_COUNT} -sU -sV -Pn"
    for num, target in enumerate(identified_targets):
        command = udp_scan_commandstr.replace("TARGET", target)
        command_dict = {
            "command": command,
            "commander_source": commander_uuid,
            "job_number": num,
            "request_share": True
        }
        udp_scan_command_list.append(command_dict)
    
    # distribute fast scan commands
    print(f"###  Performing a UDP scan using {num_valid_targets} distributed commands")
    uplink.send_distributed_commands(udp_scan_command_list)

    # poll share list until all commands are finished
    print(f"###  {num_valid_targets} distributed commands sent, waiting for completion")

    # Use slower poll interval because we expect UDP scans to take significaly longer
    udp_poll_interval = 4 * POLL_INTERVAL
    
    udp_port_scan_results = []
    # Once again, use a fancy progress bar
    pbar = tqdm(desc=f"Running UDP port scan for top {UDP_TOP_PORTS_COUNT} ports on identified targets", total=num_valid_targets)
    outstanding_jobs = list(range(num_valid_targets))
    distrib_command_meta = []

    while len(outstanding_jobs) > 0:
        time.sleep(udp_poll_interval)
        new_metadata = uplink.pop_share_data({"commander_source": commander_uuid})
        # If there's more data to process, do so
        if new_metadata:
            pbar.update(len(new_metadata))  # Relative, so add count of new metadata
            # Add to list of all metadata collected
            distrib_command_meta += new_metadata
            tqdm.write(f"{len(new_metadata)} new commands have finished since last poll... processing now")

            # Mark job ID as complete
            oldest_job_number = outstanding_jobs[0]
            to_pull = []
            for job in new_metadata:
                job_number = job.get("job_number")
                # Ensure it's not a duplicate (maybe if commander believed job was stuck)
                if job_number not in outstanding_jobs:
                    continue
                outstanding_jobs.remove(job_number)
                to_pull.append(job.get("pull_command_uuid"))

            # Check if there's any stuck jobs that should be re-distributed
            if outstanding_jobs and oldest_job_number == outstanding_jobs[0]:  # Oldest hasn't been completed and is still the oldest
                tqdm.write(f"Job {oldest_job_number} may be stuck - distribute manually if it is - '{udp_scan_command_list[oldest_job_number]}'")
                tqdm.write(f"Remaining jobs:  {outstanding_jobs}")

            # Pull back details on every valid target
            target_details_query = {"source_command": {"$in": to_pull}}
            new_scan_results = uplink.get_data(const.DEFAULT_TARGET_COLLECTION, query_filter=target_details_query)
            for new_target in new_scan_results:
                host = new_target.get('target_host')
                identified_vulns = new_target.get("vulnerabilities")
                if identified_vulns:
                    tqdm.write(f"$!$  RADAR identified the following vulnerabilities on '{host}': {identified_vulns}")
            udp_port_scan_results += new_scan_results
    pbar.close()
    # END OF PROGRESS BAR

    # Dump meta at the end
    dcommand_meta_filepath = os.path.join(output_dir, "udp_distrib_meta.json")
    tqdm.write(f"###  Saving UDP scan distributed command metadata to: '{dcommand_meta_filepath}'")
    with open(dcommand_meta_filepath, "w") as fh:
        json.dump(distrib_command_meta, fh, indent=4)
    
    # Dump files to output location
    udp_result_path = os.path.join(output_dir, "udp_port_scan.json")
    print(f"###  Saving UDP scan results to: '{udp_result_path}'")
    with open(udp_result_path, "w") as fh:
        json.dump(udp_port_scan_results, fh, indent=4)

    # Update target details w/ UDP ports
    udp_added_cols = []
    for target in udp_port_scan_results:
        indx = target.get("target_host")
        for service in target.get("services", []):
            name = f"{service.get('port')}/{service.get('protocol')}"
            # If column is not in dataframe yet, add it
            if name not in udp_added_cols:
                udp_added_cols.append(name)
                target_dataframe[name] = ""
            cell_value = service.get("version") or service.get("service") or service.get("state") or "MISSING"
            target_dataframe.at[indx, name] = cell_value

    # And save an updated version of the CSV with all service information
    dataframe_csv_path = os.path.join(output_dir, "target_details_combined.csv")
    print(f"###  Formatting target details to CSV and saving results to: '{dataframe_csv_path}'")
    target_dataframe.to_csv(dataframe_csv_path, index=False)

    # Also print out to console
    print("="*35 + " UDP PORT SCAN RESULTS " + "="*35)
    print(json.dumps(udp_port_scan_results, indent=4))
    print("="*80)

    print("#===============================================================================")
    print("#  END OF COMMANDER'S EXECUTION - HAVE A NICE DAY :)")
    print("#===============================================================================")
