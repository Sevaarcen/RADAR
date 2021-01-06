#!/usr/bin/python3
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

import cyber_radar.constants as const
from cyber_radar.distributed import DistributedWatcher
from cyber_radar.uplink_server_connection import ServerConnection


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

current_mission = const.DEFAULT_MISSION


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


def sync_data(queue, connection: ServerConnection, interval=10):
    global logger
    try:
        while True:
            logger.debug(f"Checking if data needs to be synced")
            
            if len(queue) == 0:
                time.sleep(interval)
                continue
            items_to_sync = []
            while len(queue) > 0:
                items_to_sync.append(queue.pop())
            logger.info(f"Uplink send queue contains {len(items_to_sync)} items - beginning syncing with RADAR Control Server")

            data_to_send = {}
            for to_sync in items_to_sync:
                items = to_sync.split(',', 2)
                if len(items) != 3:
                    logger.warning(f"Invalid message in queue: {to_sync}")
                    return
                database = items[0]
                collection = items[1]
                data = json.loads(items[2])
                if isinstance(data, list):
                    for document in data:
                        data_to_send.setdefault(database, {}).setdefault(collection, []).append(document)
                else:
                    data_to_send.setdefault(database, {}).setdefault(collection, []).append(data)
            
            # If there's data, sent all data to server for insertion
            if data_to_send:
                connection.bulk_send_data(data_to_send)
            # Wait before next iteration
            time.sleep(interval)
    except KeyboardInterrupt:
        logger.debug("Stopping data sync, received keyboard interrupt")


def write_queue_file(queue):
    global logger
    logger.debug("Writing send queue to file")
    if len(queue) == 0:
        logger.debug("Nothing in queue to dump")
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


def append_to_sync_queue(collection: str, data: dict):
    joined_data = f'{const.MISSION_PREFIX}{current_mission},{collection},{json.dumps(data)}'
    global send_queue
    send_queue.append(joined_data)


@app.route("/info/status", methods=["GET"])
def get_info():
    global current_mission
    global uplink_connection
    return f"Joined to the mission '{current_mission}' at {uplink_connection.server_url}"


#@method
@app.route("/mission/list", methods=["GET"])
def get_mission_list():
    global uplink_connection
    mission_list = {}
    mission_list["result"] = uplink_connection.get_mission_list()
    return mission_list


#@method
@app.route("/mission/switch", methods=["POST"])
def switch_mission():
    new_mission = request.args.get("new_mission")
    create = request.args.get("create", False, type=bool)
    if not new_mission:
        return "Did not specify mission to switch to", 400
    global logger
    global current_mission
    logger.debug(f"Current mission is '{current_mission}'")
    mission_list = uplink_connection.get_mission_list()
    # If mission does not exist, create it or error
    if not new_mission in mission_list:
        logger.debug(f"Mission '{new_mission}' not in list of {mission_list}")
        if not create:
            logger.debug("Not creating it")
            return "Mission does not exist", 404
        else:
            current_mission = new_mission
            logger.debug(f"Mission has been changed to: '{current_mission}'")
            return f"Mission is now: '{current_mission}'", 201

    # Else mission exists and can just be set
    current_mission = new_mission
    logger.debug(f"Mission has been changed to: '{current_mission}'")
    return f"Mission is now: '{current_mission}'", 200


#@method
@app.route("/authorization/info", methods=["GET"])
def is_authorized():
    global uplink_connection
    user_auth, su_auth = uplink_connection.get_authorization()
    if not user_auth:
        return f"The uplink is not authorized, using API key: '{uplink_connection.api_key}'", 401
    else:
        return f"The uplink is authorized (SU={su_auth}) with API key: '{uplink_connection.api_key}'"


#@method
@app.route("/authorization/modify", methods=["POST"])
def modify_authorization():
    api_key = request.args.get("api_key")
    if not api_key:
        return "No API key specified", 400
    is_su_string = request.args.get("superuser", "False", type=str)
    superuser = json.load(is_su_string.lower())
    is_auth_str = request.args.get("authorizing", "True", type=str)
    authorizing = json.load(is_auth_str.lower())
    global uplink_connection
    result = uplink_connection.modify_authorization(api_key, superuser=superuser, authorizing=authorizing)
    if not result:
        return f"Could not modify authorization due to error", 500
    return "API key's authorization has been modified"


#@method
@app.route("/database/info/structure", methods=["GET"])
def get_database_structure() -> dict:
    global uplink_connection
    structure = uplink_connection.get_mongo_structure()
    return structure


#@method
@app.route("/database/info/collections", methods=["GET"])
def get_collections() -> dict:
    global uplink_connection
    global current_mission
    collections = uplink_connection.get_collection_list(f"{const.MISSION_PREFIX}{current_mission}")
    return collections


#@method
@app.route("/database/data/send", methods=["POST"])
def send_data():
    collection = request.args.get("collection")
    data = request.get_json()
    if not collection:
        return "Missing 'collection' argument", 400
    append_to_sync_queue(collection, data)
    global send_queue
    global logger
    logger.info(f"Added data to send queue, now waiting to send {len(send_queue)} item(s)")
    return "Added command to send queue"


#@method
@app.route("/database/data/gather", methods=["GET"])
def get_data():
    collection = request.args.get("collection")
    if not collection:
        return "Missing 'collection' argument", 400
    global current_mission
    database = request.args.get("database", f"{const.MISSION_PREFIX}{current_mission}")
    global uplink_connection
    con_resp = uplink_connection.get_database_contents(database, collection)
    return json.dumps(con_resp)


@app.route("/database/data/query", methods=["POST"])
def query_data():
    collection = request.args.get("collection")
    if not collection:
        return "Missing 'collection' argument", 400
    global current_mission
    database = request.args.get("database", f"{const.MISSION_PREFIX}{current_mission}")

    query_filter = request.get_json(silent=True)
    if not query_filter:
        return 'Missing query as JSON payload, aborting', 400
    global uplink_connection
    con_resp = uplink_connection.query_database(database, collection, query_filter)
    return json.dumps(con_resp)


@app.route("/database/data/pop", methods=["POST"])
def pop_data():
    collection = request.args.get("collection")
    if not collection:
        return "Missing 'collection' argument", 400
    global current_mission
    database = request.args.get("database", f"{const.MISSION_PREFIX}{current_mission}")

    query_filter = request.get_json(silent=True)
    if not query_filter:
        return 'Missing query as JSON payload, aborting', 400
    global uplink_connection
    con_resp = uplink_connection.pop_shared_data(database, collection, query_filter)
    return json.dumps(con_resp)


#@method
@app.route("/distributed/submit", methods=["POST"])
def send_distributed_commands():
    commands = request.get_json()
    if not isinstance(commands, list):
        return "Commands is not an array", 400
    global uplink_connection
    uplink_connection.send_distributed_commands(commands)
    return f"{len(commands)} new commands submitted to queue"


def main():
    global logger
    parser = argparse.ArgumentParser()
    parser.add_argument('-c',
                        '--config',
                        dest='config_path',
                        type=str,
                        help="Specify non-default configuration file to use")
    arguments = parser.parse_args()

    # Make it cleanup when the program exits
    global send_queue
    mp_manager = Manager()
    send_queue = mp_manager.list()
    atexit.register(write_queue_file, send_queue)

    try:
        config_path = arguments.config_path
        if not config_path:
            import pkg_resources
            config_path = pkg_resources.resource_filename(const.PACKAGE_NAME, const.UPLINK_CONFIG)
            logger.info(f"###  User didn't specify config, falling back to default at: '{config_path}'")
        config = toml.load(config_path)
    except FileNotFoundError:
        logger.error(f"Could not find configuration file: {arguments.config_path}")
        exit(1)

    logging_level = config.get("logging-level", None)
    if logging_level:
        logger.setLevel(logging_level)

    # Push Uplink's trusted CA to environment variables for use by requests
    logger.debug("Begin processing CA / trust settings")
    using_https = config.setdefault("server", {}).get("use-https", None)
    trusted_ca = config.setdefault("server", {}).get("CA-certificate", None)
    if using_https and trusted_ca:
        absolute_path = os.path.abspath(trusted_ca)
        config.setdefault("server", {})['CA-certificate'] = absolute_path
        os.environ['REQUESTS_CA_BUNDLE'] = absolute_path

    # Initialize server connection
    logger.debug("Opening connection to RADAR Control Server")
    global uplink_connection
    uplink_connection = ServerConnection(logger, config)

    # Start daemon to sync data as it comes into the uplink
    sync_interval = config.setdefault("sync_interval", 10)
    start_sync_daemon(sync_interval)

    # Run distributed command processor
    watch_interval = config.setdefault("distributed", {}).get("watch_interval", 60)
    watcher = DistributedWatcher(append_to_sync_queue, uplink_connection, watch_interval=watch_interval)
    watcher.start()

    # Run Uplink server
    logger.debug("Starting RADAR Uplink RESTful API")
    port = config.get("port", 1684)
    # HTTP is okay here because the communication isn't external
    # Bind to localhost only to not allow external communication
    app.run(host=const.LOCAL_COMM_ADDR, port=port)


if __name__ == '__main__':
    main()
