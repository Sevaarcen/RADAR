from flask import Flask, request, jsonify
from pymongo import MongoClient
from pymongo.errors import ServerSelectionTimeoutError
import bson.json_util
import json
import base64
import binascii


# Default RADAR Control Server configuration
default_config = {
    'host': '0.0.0.0',
    'port': 1794,
    'database': 'mongodb://localhost:27017/',
    'database_timeout': 2000
}

# Hook the server into Flask
app = Flask(__name__)

# Database variables
database_client = None
PROTECTED_DATABASES = [  # Databases which the API shouldn't access
    'admin',
    'config',
    'local'
]
RESTRICTED_DATABASES = [  # Databases which should only be accessed by superusers
    'radar-control'
]


# Print site map / API reference on the index
@app.route('/', methods=['GET'])
def return_api_reference():
    routes = "<html>"
    for rule in app.url_map.iter_rules():
        routes += f'{rule}<br>'
    routes += "</html>"
    return routes, 200


# List databases and collections in those databases
@app.route('/info/database', methods=['GET'])
def list_databases():
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


# Raw connection to list contents of database
@app.route('/database/<db_name>/<collection_name>/list', methods=['GET'])
def database_list_data(db_name, collection_name):
    print(f'###  Viewing data from {db_name}.{collection_name}')
    for protected in PROTECTED_DATABASES:
        if db_name == protected:
            return '', 403
    # Ensure user has access
    for restricted in RESTRICTED_DATABASES:
        if restricted == db_name and not is_authorized(superuser_permissions=True):
            return '', 401
    global database_client
    database = database_client[db_name]
    collection = database[collection_name]
    query_results = collection.find()
    json_string = bson.json_util.dumps(query_results)
    return jsonify(json.loads(json_string)), 200


# Raw connection to insert into database
@app.route('/database/<db_name>/<collection_name>/insert', methods=['POST'])
def database_insert_data(db_name, collection_name):
    print(f'###  Inserting at {db_name}.{collection_name}')
    # Ensure database is not protected
    for protected in PROTECTED_DATABASES:
        if db_name == protected:
            return '', 403
    # Ensure user has access
    for restricted in RESTRICTED_DATABASES:
        if restricted == db_name and not is_authorized(superuser_permissions=True):
            return '', 401
    encoded_data = request.get_data()
    try:
        # Parse data and get ready for insertion
        print(encoded_data)
        raw_data = base64.b64decode(encoded_data).decode()
        print(raw_data)
        json_data = json.loads(raw_data)
        # Load database
        global database_client
        database = database_client[db_name]
        collection = database[collection_name]
        result = collection.insert_one(json_data)
        print(result.inserted_id)
    except (binascii.Error, json.decoder.JSONDecodeError) as err:
        return "Invalid data, it must be base 64 encoded json", 400

    return request.get_data(), 200


@app.route('/clients/request', methods=['GET'])
def request_client_authorization():
    username = request.args.get('username')
    remote_host = request.remote_addr
    if username and remote_host:
        global database_client
        radar_control_database = database_client['radar-control']
        client_collection = radar_control_database['clients']
        full_request = {
            'username': username,
            'from': remote_host,
            'authorized': False,
            'level': 'user'
        }
        if number_of_clients() == 0:
            full_request['level'] = 'superuser'
            full_request['authorized'] = True
        matching_clients = client_collection.find({'username': username, 'from': remote_host})
        if len(list(matching_clients)) != 0:
            return 'User has already submitted a request', 400
        # Insert into Database
        client_collection.insert_one(full_request)
        return jsonify(full_request), 200
    else:
        return "You must specify a username, superuser is optional", 400


# TODO make this not by host, but rather user. Perhaps just use SSH?
@app.route('/clients/authorize')
def authorize_client():
    username = request.args.get('username')
    level = 'superuser' if request.args.get('superuser') == 'True' else 'user'
    if not username:
        return 'You must specify a username', 400
    if is_authorized(superuser_permissions=True):
        global database_client
        radar_control_database = database_client['radar-control']
        client_collection = radar_control_database['clients']
        query = {'authorized': False, 'username': username}
        query_results = client_collection.find_one_and_update(query, {'$set': {'authorized': True, 'level': level}})
        return bson.json_util.dumps(query_results), 200
    else:
        return 'You must be a superuser', 401


# TODO Make this actually secure rather than just being from the correct host
def is_authorized(superuser_permissions=False):
    from_address = request.remote_addr
    print(f'Authorizing from {from_address}')
    # Grab registered client info from database
    global database_client
    radar_control_database = database_client['radar-control']
    client_collection = radar_control_database['clients']
    # Build search filter
    query = {'authorized': True, 'from': from_address}
    if superuser_permissions:
        query['level'] = 'superuser'
    # Run query
    query_result = list(client_collection.find(query))
    # Return count of matches isn't 0
    return len(query_result) > 0


# Return number of authorized clients
def number_of_clients():
    global database_client
    radar_control_database = database_client['radar-control']
    client_collection = radar_control_database['clients']
    query_result = list(client_collection.find({'authorized': True}))
    return len(query_result)


def start():
    # Connect to database
    global database_client
    database_client = MongoClient(default_config['database'], serverSelectionTimeoutMS=default_config['database_timeout'])
    try:
        database_client.server_info()
        print(f"$$$  Connected to backend MongoDB at {default_config['database']}")
    except ServerSelectionTimeoutError as error:
        print(f"!!!  Stopping server, could not connect to MongoDB at {default_config['database']}")
        exit(1)

    # Start Flask API server
    app.run(debug=True, host=default_config['host'], port=default_config['port'])


if __name__ == '__main__':
    start()
