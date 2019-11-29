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
import argparse

import logging
import time
import sys
import os
import json
import toml
import atexit

from multiprocessing import Process, Manager
from flask import Flask, request, Response
from jsonrpcserver import method, dispatch

import radar.constants as const
from radar.distributed import DistributedWatcher
from radar.uplink_server_connection import ServerConnection


# Global variables
app = Flask(__name__)

# Logging setup
logger = logging.getLogger('uplink_logger')
handler = logging.StreamHandler(stream=sys.stdout)
logger.addHandler(handler)
logger.setLevel(logging.DEBUG)

# Uplink control variables
uplink_connection: ServerConnection = None
send_queue = None


def start_sync_daemon(sync_interval):
    global logger   
    logger.debug("Sync daemon starting")
    global send_queue
    global uplink_connection
    if os.path.exists(const.UPLINK_SAVED_QUEUE_FILENAME):
        logger.debug("The queue file exists")
        queue_file = open("uplink_queue.txt", "r")
        for item in queue_file:
            if item.strip() != '':
                send_queue.append(item.strip())
            logger.debug("Item loaded into queue")
        logger.debug(f"Send queue now contains {len(send_queue)} items")
        queue_file.close()
        os.remove(const.UPLINK_SAVED_QUEUE_FILENAME)
    sync_daemon = Process(target=sync_data, args=(send_queue, uplink_connection, sync_interval,))
    sync_daemon.daemon = True
    sync_daemon.start()
    logger.debug("Sync daemon started")


def sync_data(queue, connection, interval=10):
    global logger
    try:
        while True:
            logger.debug(f"Checking if data needs to be synced")
            while len(queue) != 0:
                logger.debug("Syncing data with RADAR Control Server")
                to_sync = queue.pop()
                items = to_sync.split(',', 1)
                if len(items) != 2:
                    logger.warning(f"Invalid message in queue: {to_sync}")
                    return
                try:
                    collection = items[0]
                    data = json.loads(items[1])
                    result = connection.send_to_database(collection, data)
                    print(f"SENT? = {result}")
                    logger.debug(f"Done... {len(queue)} remaining")
                except json.decoder.JSONDecodeError:
                    logger.error("Invalid JSON data in queue")
                    logger.debug(items[1])
            time.sleep(interval)
            sync_data(queue, connection, interval=interval)
    except KeyboardInterrupt:
        logger.debug("Stopping data sync, received keyboard interrupt")


def write_queue_file(queue):
    global logger
    logger.debug("Writing send queue to file")
    if len(queue) == 0:
        logger.debug("Nothing in queue")
        return
    logger.debug(f"{len(queue)} items in queue during cleanup")
    try:
        queue_file = open(const.UPLINK_SAVED_QUEUE_FILENAME, 'w')
        for item in queue:
            if item != '':
                queue_file.write(f'{item}\n')
        queue_file.close()
    except PermissionError:
        logger.error("Could not create uplink queue file, the queue will be lost!")
        logger.debug(send_queue)


@app.route("/", methods=["POST"])
def handle_request():
    if request.remote_addr != '127.0.0.1':
        return "no", 403
    req = request.get_data().decode()
    response = dispatch(req)
    return Response(str(response), response.http_status, mimetype="application/json")


@method
def get_info():
    global uplink_connection
    return f"Joined to the mission {uplink_connection.mission} at {uplink_connection.server_url}"


@method
def get_mission_list():
    global uplink_connection
    mission_list = uplink_connection.get_mission_list()
    print(mission_list)
    return mission_list


@method
def switch_mission(new_mission: str, create=False):
    global uplink_connection
    mission_list = uplink_connection.get_mission_list()
    assert new_mission in mission_list or create, "Mission doesn't exist"
    uplink_connection.mission = new_mission
    return f"Mission is now: '{uplink_connection.mission}'"


@method
def is_authorized():
    global uplink_connection
    user_auth, su_auth = uplink_connection.get_authorization()
    if not user_auth:
        return f"The uplink is not authorized, using API key: '{uplink_connection.api_key}'"
    else:
        return f"The uplink is authorized (SU={su_auth}) with API key: '{uplink_connection.api_key}'"


@method
def modify_authorization(api_key, superuser=False, authorizing=True):
    global uplink_connection
    result = uplink_connection.modify_authorization(api_key, superuser=superuser, authorizing=authorizing)
    assert result, "Could not be completed"
    return result


@method
def get_database_structure():
    global uplink_connection
    structure = uplink_connection.get_mongo_structure()
    return structure


@method
def get_collections():
    global uplink_connection
    collections = uplink_connection.get_collection_list()
    return collections


@method
def send_data(collection, data):
    assert isinstance(data, (dict, list)), "The data must be json!"
    joined_data = f'{collection},{json.dumps(data)}'
    global send_queue
    send_queue.append(joined_data)
    global logger
    logger.info(f"Added data to send queue, now waiting to send {len(send_queue)} item(s)")
    return "Added command to send queue"


@method
def get_data(collection, database=None):
    global uplink_connection
    con_resp = uplink_connection.get_database_contents(collection, database=database)
    return con_resp


@method
def send_distributed_command(command):
    global uplink_connection
    uplink_connection.send_distributed_command(command)
    return "Done"


def main():
    global logger
    logger.info
    parser = argparse.ArgumentParser()
    parser.add_argument('-c',
                        '--config',
                        dest='config_path',
                        type=str,
                        default=const.UPLINK_CONFIG,
                        help="Specify non-default configuration file to use")
    arguments = parser.parse_args()

    # Make it cleanup when the program exits
    global send_queue
    mp_manager = Manager()
    send_queue = mp_manager.list()
    atexit.register(write_queue_file, send_queue)

    try:
        config = toml.load(arguments.config_path)
    except FileNotFoundError:
        logger.error(f"Could not find configuration file: {arguments.config_path}")
        exit(1)

    # Push Uplink's trusted CA to environment variables for use by requests
    trusted_ca = config.setdefault("server", {}).get("CA-certificate", None)
    if trusted_ca:
        absolute_path = os.path.abspath(trusted_ca)
        config.setdefault("server", {})['CA-certificate'] = absolute_path
        os.environ['REQUESTS_CA_BUNDLE'] = absolute_path

    # Initialize server connection
    global uplink_connection
    uplink_connection = ServerConnection(logger, config)
    uplink_connection.open_connection()

    # Start daemon to sync data as it comes into the uplink
    sync_interval = config.setdefault("sync_interval", 10)
    start_sync_daemon(sync_interval)

    # Run distributed command processor
    watcher = DistributedWatcher(uplink_connection)
    watcher.start()

    # Run Uplink server
    port = config.get("port", 1684)
    # HTTP is okay here because the communication isn't external
    app.run(host="127.0.0.1", port=port)


if __name__ == '__main__':
    main()
