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

#!/usr/bin/python

import os
import argparse
import toml
import json
import base64
import binascii
import sys
import logging
import time
import secrets
import bson.json_util

from typing import MutableMapping
from flask import Flask, request, jsonify
from pymongo import MongoClient
from pymongo.errors import ServerSelectionTimeoutError

import cyber_radar.constants as const


# Hook the server into Flask
app = Flask(__name__)

# Global variables
database_client = None
distributed_command_queue = []
stdout = None
stderr = None


# Send site map / low-quality API reference on the index
@app.route('/', methods=['GET'])
def return_api_reference():
    """ This method provides a listing of the available pages "routes" served by Flask.
    :return: Tuple containing HTML response and HTTP status code
    """
    routes = "<html>"
    for rule in app.url_map.iter_rules():
        routes += f'{rule}<br>'
    routes += "</html>"
    return routes, 200


# List databases and collections in those databases
@app.route('/info/database', methods=['GET'])
def list_databases():
    """ This method will list the databases and collections contained in the MongoDB.
    :return: Tuple containing the JSON response and HTTP status code
    """
    if not is_authorized():
        return 'Unauthorized user', 401
    global database_client
    output = {}
    # For every database name
    for database_name in database_client.list_database_names():
        collection_names = []
        # Get a list of collections
        for collection in database_client[database_name].list_collections():
            # Get the name of each collection and add it to a list
            collection_names.append(collection['name'])
        # Then add that list as the value with the database name as the key
        output[database_name] = collection_names
    # Return dictionary of databases and collections
    return output, 200


# Returns if the user is authorized
@app.route('/info/authorized', methods=['GET'])
def return_is_authorized():
    """ This method gives information about the requester's authentication status
    :return: A tuple containing the JSON response and HTTP status code
    """
    base_result = is_authorized()
    su_result = is_authorized(superuser_permissions=True)
    result = {
        'Authorized': base_result,
        'Superuser': su_result
    }
    return result, 200


@app.route('/info/missions', methods=['GET'])
def get_mission_list():
    """ This method returns the mission list
    :return: A string of mission names, seperated by commas
    """
    if not is_authorized():
        return 'Unauthorized user', 401
    global database_client
    result = ""
    for database_name in database_client.database_names():
        if const.MISSION_PREFIX in database_name:
            result += database_name[len(const.MISSION_PREFIX):] + ","
    result = result[0:-1]  # Remove the trailing ','
    return result


# Raw connection to list contents of database
@app.route('/database/<db_name>/<collection_name>/list', methods=['GET', 'POST'])
def database_list_data(db_name, collection_name):
    """ This method provides a full list of the contents of a specific database collection.
    This method will protect the database. Protected databases are not accessible via this method.
    Restricted databases can only be accessed by authorized superusers.
    :param db_name: Name of Database in MongoDB
    :param collection_name: Name of Collection in MongoDB
    :return: A tuple containg the JSON response and HTTP status code
    """
    if not is_authorized():
        return 'Unauthorized user', 401
    stdout.write(f'###  Viewing data from {db_name}.{collection_name}\n')
    stdout.flush()
    for protected in const.PROTECTED_DATABASES:
        if db_name == protected:
            return "DB is protected and can't be accessed by the API", 403
    # Ensure user has access
    for restricted in const.RESTRICTED_DATABASES:
        if restricted == db_name and not is_authorized(superuser_permissions=True):
            return "DB is restricted and you don't have correct access", 401
    global database_client
    database = database_client[db_name]
    collection = database[collection_name]
    # Simple GET means retrieve all data
    if request.method == "GET":
        query_results = collection.find()
        json_string = bson.json_util.dumps(query_results)
        return jsonify(json.loads(json_string)), 200
    # Post means use JSON filter to only get specific results
    elif request.method == "POST":
        query_filter = request.get_json(silent=True)
        if not query_filter:
            return "User failed to specify filter as JSON payload of POST request", 400
        query_results = collection.find(query_filter)
        json_string = bson.json_util.dumps(query_results)
        return jsonify(json.loads(json_string)), 200


@app.route('/database/<db_name>/<collection_name>/pop', methods=['POST'])
def database_pop_data(db_name, collection_name):
    """[summary]

    Args:
        db_name (str): Name of database (must be a mission)
        collection_name (str): Name of collection (must be the share collection)

    Returns:
        [type]: [description]
    """
    # make sure client is authorized with superuser permissions (since we're deleting data)
    if not is_authorized(superuser_permissions=True):
        return 'Unauthorized user, must have SU permissions', 401
    # Make sure DB isn't protected or restricted
    if db_name in const.PROTECTED_DATABASES or db_name in const.RESTRICTED_DATABASES:
        return "The database is not valid and cannot be popped from the API", 403
    # Make sure collection is labelled as the collection where temp data is shared
    if collection_name != const.DEFAULT_SHARE_COLLECTION:
        return "Can only pop data from share collection", 400
    # Wrangle filter for what to pop (e.g. by commander id)
    query_filter = request.get_json(silent=True)
    if not query_filter:
        return "User failed to specify filter as JSON payload of POST request", 400

    stdout.write(f'###  Popping data from {db_name}.{collection_name}\n')
    stdout.flush()

    # Now we are ready to gather and then delete data
    global database_client
    database = database_client[db_name]
    collection = database[collection_name]

    # Gather results
    find_results = collection.find(query_filter)
    json_result_string = bson.json_util.dumps(find_results)

    # Then delete them (hence the pop)
    delete_results = collection.delete_many(query_filter)
    stdout.write(f'$$$  Popped {delete_results.deleted_count} documents from {db_name}.{collection_name}\n')
    stdout.flush()    

    return jsonify(json.loads(json_result_string)), 200


# Raw connection to insert into database
@app.route('/database/<db_name>/<collection_name>/insert', methods=['POST'])
def database_insert_data(db_name, collection_name):
    """ This method will insert the POST data from the request into the specified database's collection.
    :param db_name: Name of database where the data is being inserted
    :param collection_name: Name of collection where the data is being inserted
    :return: A tuple containg a plain-text response and HTTP status code
    """
    stdout.write(f'###  Database inserting data at {db_name}.{collection_name}\n')
    stdout.flush()
    # Ensure database is not protected
    if not is_authorized():
        return 'Unauthorized user', 401
    for protected in const.PROTECTED_DATABASES:
        if db_name == protected:
            return 'Cannot access protected DB via API', 403
    # Ensure user has access
    for restricted in const.RESTRICTED_DATABASES:
        if restricted == db_name and not is_authorized(superuser_permissions=True):
            return 'DB restricted to superusers', 401
    encoded_data = request.get_data()
    try:
        # Parse data and get ready for insertion
        raw_data = base64.b64decode(encoded_data).decode()
        parsed_data = json.loads(raw_data)

        # Load database
        global database_client
        database = database_client[db_name]
        collection = database[collection_name]

        # Handle inserting the data
        if isinstance(parsed_data, dict):
            parsed_data.update({'inserted_at': time.time()})
            collection.insert_one(parsed_data)
        elif isinstance(parsed_data, list):
            for item in parsed_data:
                if not isinstance(item, dict):
                    return "If it's a list data must exclusively contain JSON", 400
                item.update({'inserted_at': time.time()})
                collection.insert_one(item)
        else:
            return f"Unknown type of data: {type(parsed_data)}", 400
    except (TypeError, binascii.Error, json.decoder.JSONDecodeError):
        return "Invalid data, it must be base 64 encoded json", 400

    return 'Inserted data successfully', 200


# Raw connection to insert into database
@app.route('/database/bulk-insert', methods=['POST'])
def bulk_insert_data():
    """ This method will insert the POST data from the request into the specified database's collection.
    :return: A tuple containg a plain-text response and HTTP status code
    """
    if not is_authorized():
        return 'Unauthorized user', 401
    
    insert_data_dict = request.get_json(silent=True)
    if not insert_data_dict:
        return "User failed to specify bulk insert data as JSON payload of POST request", 400

    stdout.write(f'###  Database performing bulk insert of data\n')
    stdout.flush()

    # Double check the databases are valid before trying to write anything
    for db_name in insert_data_dict.keys():
        if db_name in const.PROTECTED_DATABASES:
            return 'Cannot access protected databased via API', 403
        elif db_name in const.RESTRICTED_DATABASES:
            return "Cannot bulk write to restricted databases", 403

    # Insert requested data
    global database_client
    success_count = 0
    for database_name, database_dict in insert_data_dict.items():
        for collection_name, document_list in database_dict.items():
            stdout.write(f"---  Inserting {len(document_list)} documents into {database_name}.{collection_name}\n")
            stdout.flush()
            result = database_client[database_name][collection_name].insert_many(document_list)
            success_count += len(result.inserted_ids)
    stdout.write(f'###  During a bulk write, successfully inserted a total of {success_count} documents into the database\n')
    stdout.flush()
    return f"Successfully inserted {success_count} documents into the database", 200


@app.route('/clients/request', methods=['GET'])
def request_client_authorization():
    """ This method will insert the client into the database given a username as a GET parameter.
    If no clients are in the database, the requester is automatically authorized and granted superuser privileges.
    This method will not submit duplicate requests.
    :return: A tuple containing the JSON response and HTTP status code
    """
    username = request.args.get('username')
    remote_host = request.remote_addr
    friendly_user_auth_string = f'{username}@{remote_host}'
    if username and remote_host:
        global database_client
        radar_control_database = database_client['radar-control']
        client_collection = radar_control_database['clients']
        full_request = {
            'friendly_name': friendly_user_auth_string,
            'authorized': False,
            'level': 'user'
        }
        # Automatically grant authorization if no clients exist yet or the request is from localhost
        if number_of_clients() == 0 or remote_host == '127.0.0.1':
            full_request['level'] = 'superuser'
            full_request['authorized'] = True
        matching_clients = client_collection.find({'friendly_name': friendly_user_auth_string})
        if len(list(matching_clients)) != 0:
            return "", 200  # Don't return API key to prevent any errors causing leaked data
        # Insert into Database
        api_key = secrets.token_hex(16)
        full_request['key'] = api_key
        client_collection.insert_one(full_request)
        return api_key, 200
    else:
        return "You must specify a username", 400


@app.route('/clients/authorize', methods=['GET'])
def authorize_client():
    """ This method will authorize clients given a username as a GET parameter. You may also specify 'superuser=True'
    to authorize the user as a superuser. This functionality can only be accessed by a superuser/
    :return: A tuple containing a plain-text response and HTTP status code
    """
    key = request.args.get('key')
    level = 'superuser' if request.args.get('superuser') == 'True' else 'user'
    if not key:
        return 'You must specify an API key to authorize', 400
    if is_authorized(superuser_permissions=True):
        global database_client
        radar_control_database = database_client['radar-control']
        client_collection = radar_control_database['clients']
        query = {'authorized': False, 'key': key}
        query_results = client_collection.update_many(query, {'$set': {'authorized': True, 'level': level}})
        return f"Authorized {query_results.matched_count} clients", 200
    else:
        return 'You must be a superuser', 401


@app.route('/clients/deauthorize', methods=['GET'])
def deauthorize_client():
    """ For a given API key, remove it from the list of authorized clients. Only callable by superusers.
    """
    key = request.args.get('key')
    if not key:
        return 'You must specify an API key to deauthorize', 400
    if is_authorized(superuser_permissions=True):
        global database_client
        radar_control_database = database_client['radar-control']
        client_collection = radar_control_database['clients']
        query = {'authorized': True, 'key': key}
        query_results = client_collection.update_many(query, {'$set': {'authorized': False}})
        return f"De-authorized {query_results.matched_count} clients", 200
    else:
        return 'You must be a superuser', 401


@app.route('/distributed/get', methods=['GET'])
def pop_distributed_command():
    """ Returns a JSON element that contains a system command
    """
    if not is_authorized():
        return 'You are not authorized', 401
    global distributed_command_queue
    if len(distributed_command_queue) == 0:
        return "Nothing in queue", 304
    else:
        return distributed_command_queue.pop(), 200


@app.route('/distributed/add', methods=['POST'])
def add_distributed_command():
    """ Endpoint used to add arbitrary system commands to a queue that clients will pull from.
    Only superusers can add commands to this queue (for security and integrity reasons).
    Commands in this queue are dicts that contain the 'command' key and option arbitrary metadata in other keys.
    """
    if not is_authorized(superuser_permissions=True):
        return 'You must be a superuser', 401
    try:
        command_list = request.get_json()
        if not isinstance(command_list, list):
            raise TypeError(f"Not a list, was given a {type(command_list)}")
        for command in command_list:
            if not isinstance(command, dict) or not command.get("command"):
                raise ValueError(f"Invalid command dict in list - missing 'command' key - {command}")
    except (TypeError, ValueError) as err:
        return f'Malformed data: {err}', 400
    global distributed_command_queue
    # Append new commands into queue
    for command in command_list:
        distributed_command_queue.insert(0, command)
    return 'Added command to queue', 200


def is_authorized(superuser_permissions=False):
    """ This internal method is used to verify the client is authorized.
    :param superuser_permissions: This will cause the method to only be true if the client is an authorized superuser.
    :return: True when the user is authorized, False otherwise
    """
    from_address = request.remote_addr
    global stdout
    if from_address == '127.0.0.1':
        stdout.write('###  Authorization skipped, permission automatically granted for localhost\n')
        stdout.flush()
        return True
    # Grab registered client info from database
    global database_client
    radar_control_database = database_client['radar-control']
    client_collection = radar_control_database['clients']
    # Build search filter
    key = request.cookies.get('key', None)
    if not key:
        stdout.write('###  Client checked auth but is missing the key\n')
        stdout.flush()
        return False
    query = {'authorized': True, 'key': key}
    if superuser_permissions:
        query['level'] = 'superuser'
    # Run query
    query_result = list(client_collection.find(query))
    # Return count of matches isn't 0
    authorized = len(query_result) > 0
    if not authorized:
        stdout.write("!!!  Client not authorized\n")
        stdout.flush()
    return authorized


# Return number of authorized clients
def number_of_clients() -> int:
    """ This internal method returns the number of authorized clients in the database.
    :return: The number of authorized clients.
    """
    global database_client
    radar_control_database = database_client['radar-control']
    client_collection = radar_control_database['clients']
    query_result = list(client_collection.find({'authorized': True}))
    return len(query_result)


def verify_config(config: MutableMapping) -> bool:
    global stderr
    critical_error = False
    # Verify web_server section (required)
    web_server = config.get('web_server', None)
    if not web_server:
        stderr.write("!!!  Server config missing 'web_server' section\n")
        stderr.flush()
        critical_error = True
    else:
        listen_address = web_server.get('listen_address', None)
        if not listen_address:
            stderr.write("!!!  Server config missing 'listen_address' in 'web_server' section, assuming default\n")
            stderr.flush()
        port = web_server.get('port', None)
        if not port:
            stderr.write("!!!  Server config missing 'port' in 'web_server' section, assuming default\n")
            stderr.flush()

    # Verify certificates section (optional)
    certificates = config.get('certificates', None)
    if not certificates:
        stderr.write("!!!  Server config missing 'certificates' section, it will run an insecure HTTP API instead\n")
        stderr.flush()
    else:
        private_key = certificates.get("private_key", None)
        if not private_key:
            stderr.write("!!!  Server config missing 'private_key' in 'certificates' section\n")
            stderr.flush()
            critical_error = True
        public_key = certificates.get("public_key", None)
        if not public_key:
            stderr.write("!!!  Server config missing 'public_key' in 'certificates' section\n")
            stderr.flush()
            critical_error = True

    # Verify database section
    database = config.get('database', None)
    if not database:
        stderr.write("!!!  Server config missing 'database' section\n")
        stderr.flush()
        critical_error = True
    else:
        database_host = database.get('host', None)
        if not database_host:
            stderr.write("!!!  Server config missing 'host' in 'database' section\n")
            stderr.flush()
            critical_error = True
        database_port = database.get('port', None)
        if not database_port:
            stderr.write("!!!  Server config missing 'port' in 'database' section, assuming default port\n")
            stderr.flush()
        database_username = database.get('username', None)
        if not database_username:
            stderr.write("!!!  Server config missing 'username' in 'database' section, assuming no credentials\n")
            stderr.flush()
        database_password = database.get('password', None)
        if not database_password:
            stderr.write("!!!  Server config missing 'password' in 'database' section, assuming no credentials\n")
            stderr.flush()
        database_timeout = database.get('timeout', None)
        if not database_timeout:
            stderr.write("!!!  Server config missing 'timeout' in 'database' section, assuming default\n")
            stderr.flush()

    return not critical_error


def start(use_stdout=sys.stdout, use_stderr=sys.stderr, config_filepath=None, dry_run=False):
    """ This internal method is used to start the Flask web server and connect to the backend Mongo database.
    :param use_stdout: A stream to use for stdout instead of sys.stdout
    :param use_stderr: A stream to use for stderr instead of sys.stderr
    :param dry_run: True if the server shouldn't actually be started
    :return: None if dry_run is False, otherwise return a str with the results of the dry run
    """
    # Send output to specified place
    global stdout
    stdout = use_stdout
    global stderr
    stderr = use_stderr
    # Make Flask logger also use these
    flask_logger = logging.getLogger('werkzeug')
    stdout_handler = logging.StreamHandler(stdout)
    flask_logger.addHandler(stdout_handler)

    try:
        if not config_filepath:
            import pkg_resources
            config_filepath = pkg_resources.resource_filename(const.PACKAGE_NAME, const.SERVER_CONFIG)
            stderr.write(f"###  User didn't specify config, falling back to default at: '{config_filepath}'\n")
        server_config = toml.load(config_filepath)
    except FileNotFoundError:
        stderr.write(f"!!!  Could not find configuration file {config_filepath}, server will shut down\n")
        stderr.flush()
        exit(2)

    if not verify_config(server_config):
        stderr.write("!!!  Invalid configuration file, server shutting down\n")
        stderr.flush()
        exit(3)

    # Connect to database
    global database_client
    db_host = server_config['database']['host']
    db_port = server_config['database'].get('port', 27017)
    db_user = server_config['database'].get('username', None)
    db_password = server_config['database'].get('password', None)
    db_timeout = server_config['database'].get('timeout', 2000)
    if db_user and db_password:
        mongo_database_url = f"mongodb://{db_user}:{db_password}@{db_host}:{db_port}"
    else:
        mongo_database_url = f"mongodb://{db_host}:{db_port}"
    database_client = MongoClient(mongo_database_url, serverSelectionTimeoutMS=db_timeout)
    try:
        database_client.server_info()
        stdout.write(f"$$$  Connected to backend Mongo database\n")
        stdout.flush()
    except ServerSelectionTimeoutError as error:
        stderr.write(f"!!!  Stopping server, could not connect to MongoDB with URL {mongo_database_url}\n")
        stderr.write(str(error) + "\n")
        stderr.flush()
        exit(1)

    # Grab web server information
    listen_address = server_config['web_server'].get('listen_address', "0.0.0.0")
    listen_port = server_config['web_server'].get('port', 1794)

    # Grab certificate info if available
    public_key_file = server_config.get('certificates', {}).get('public_key', None)
    private_key_file = server_config.get('certificates', {}).get('private_key', None)

    # And start server
    if public_key_file and private_key_file:
        stdout.write("###  Starting HTTPS RADAR Control Server\n")
        stdout.flush()
        context = (public_key_file, private_key_file)
        if os.path.exists(public_key_file) and os.path.exists(private_key_file):
            if not dry_run:
                app.run(host=listen_address, port=listen_port, ssl_context=context)
            else:
                stdout.write("DRY RUN COMPLETE\n")
                stdout.flush()
                return "HTTPS = SUCCESS"
        else:
            stderr.write("!!!  Certificate and/or key file could not be found! Starting server w/ HTTP instead\n")
            stderr.flush()
            if not dry_run:
                app.run(host=listen_address, port=listen_port)
            else:
                stdout.write("DRY RUN COMPLETE\n")
                stdout.flush()
                return "HTTPS = FAIL, HTTP = SUCCESS"
    else:
        if not dry_run:
            app.run(host=listen_address, port=listen_port)
        else:
            stdout.write("DRY RUN COMPLETE\n")
            stdout.flush()
            return "HTTP = SUCCESS"


if __name__ == '__main__':
    # Parse arguments
    parser = argparse.ArgumentParser()
    parser.add_argument('-c',
                        '--config',
                        dest='config_path',
                        type=str,
                        help="Specify non-default configuration file to use")
    arguments = parser.parse_args()

    start(config_filepath=arguments.config_path)
