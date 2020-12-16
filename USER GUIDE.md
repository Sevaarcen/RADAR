# Getting Started

Once you have RADAR on your central host, the first step is to setup the RADAR control server where clients connect and send data.


## Connection Diagram
Below is a diagram showing how each component of RADAR is connected.

1. Provide your own Mongo database to host the data. This can be a container, or a bare-metal database. Follow installation instructions for your operating system and preference. Set this up prior to configuring RADAR.
2. The next componenet is the "RADAR Control Server" (`radar-server.py`). This is the central server that brokers data and distributes work to connected machines. This server is configured to connect to the database and accept connections from the uplinks.
3. Each host that clients will use will then host a RADAR Uplink Server (`radar-uplink.py`). This server is used to buffer data and communicate with the Control Server to improve client performance. This server allows distributed jobs to run in the background.
4. Users interact with RADAR through the clients. `radar.py` is used for running system commands via RADAR, and `radar-ctl.py` is used to interact with RADAR's control functions. The client runs until completion and relies on the Uplink to sync the data afterwards.
```

                                                                          +----------------------------+       +---------------------------+
                                                                          |                            |       |                           |
                                                                          |    RADAR Uplink Server     |       |       RADAR Clients       |
                                                                 +--------+  (one per host w/ client)  +-------+ (radar.py / radar-ctl.py) |
                                                                 |        |                            |       |                           |
                                                                 |        +----------------------------+       +---------------------------+
                                                                 |
 +---------------------------+                                   |
 |                           |       +----------------------+    |        +----------------------------+       +---------------------------+
 |                           |       |                      |    |        |                            |       |                           |
 |      Mongo Database       |       |                      |    |        |    RADAR Uplink Server     |       |       RADAR Clients       |
 |   (external dependency)   +-------+ RADAR Control Server +-------------+  (one per host w/ client)  +-------+ (radar.py / radar-ctl.py) |
 |  (set this up beforehand) |       |                      |    |        |                            |       |                           |
 |                           |       |                      |    |        +----------------------------+       +---------------------------+
 |                           |       +----------------------+    |
 +---------------------------+                                   |
                                                                 |        +----------------------------+       +---------------------------+
                                                                 |        |                            |       |                           |
                                                                 +--------+    RADAR Uplink Server     +-------+       RADAR Clients       |
                                                                          |  (one per host w/ client)  |       | (radar.py / radar-ctl.py) |
                                                                          |                            |       |                           |
                                                                          +----------------------------+       +---------------------------+


```
## First Steps

1. Clone this repository on your computer. For all my examples, I am using either CentOS 8 or Fedora 31.
```bash
git clone https://github.com/Sevaarcen/RADAR.git
```

2. Install system and python packages
```
sudo pip install -r requirements.txt
sudo ./install_system_packages.sh # Or install packages listed in README.md
```

# Steps to Setup RADAR Control Server

The RADAR Control Server is the central server which controls all clients and handles all communication to the backend Mongo database.

1. Start a Mongo Database. The root account should match the credentials in ```server_config.toml```. Using podman on RHEL this could look like:
    ```
    sudo podman run -d --name radar_database -p 27017:27017 -e MONGO_INITDB_ROOT_USERNAME=root -e MONGO_INITDB_ROOT_PASSWORD=R4d4rD4t4b4s3 mongo:latest
    ```
2. (OPTIONAL) Generate certificates to allow the website to use HTTPS
3. If applicable, allow the port through your firewall
    ```
    sudo firewall-cmd --add-port=1794/tcp --permanent
    sudo firewall-cmd --reload
    ``` 
4. Start the RADAR Control Server using the ```server.py``` script
5. Keep the console open, closing the script will shutdown the server

## Using an HTTP server instead of HTTPS

To use HTTP instead of HTTPS (only suggested for development or testing), just comment out the `certificates` portion of the config file.


# Steps to Setup RADAR Uplink Server

A RADAR Uplink Server is a server which runs on every host which has a RADAR Client. This server's job is to manage communication between the client and server and offload responsibility from the client so it runs as quickly as possible.

1. (IF USING HTTPS) Copy your root CA public key to the file path specified in ```uplink_config.toml```. By default this is a file called ```rootCA.pem`` in the RADAR base directory.
2. Ensure the ```host``` key in the config file exactly matches the CN of the certificate.
3. Start the RADAR Uplink Server using the ```uplink_server.py``` script.
4. Keep the console open, closing the script will shutdown the server

## Connecting to HTTP instead of HTTPS

In `uplink_config.toml` make sure the following line is set: `use-https = false`.

## Uplink Authorization
The first Uplink to connect to the Control Server is automatically granted Superuser permissions. Any additional Uplinks require authorization (see the `grant-auth` command in the internal client).

> Note: Any Uplink connecting from `127.0.0.1` is always authorized



# Steps to Setup RADAR Client

A RADAR Client's purpose is to ingest system command output and provide an interface to manage the RADAR environment.

1. Ensure client files are executable `chmod +x client.py radar_internal.py`
1. Ensure your local RADAR Uplink server is running.
2. If you changed your Uplink's settings you may need to ensure the `client_config.toml` file is configured correctly.

# Usage / Examples

## Using the RADAR Client
The primary `client.py` client is to execute commands and send the results for parsing, automation, and syncing with the database.

Usage: `./client.py <COMMAND_HERE>`

E.g.
```
./client.py nmap scanme.nmap.org -sV
```

## Using the RADAR Internal Client
The `radar_internal.py` client is to communicate with the Uplink and Control Server. This client allows for the retrieval of data in addition to some special commands that are in the list below. 

Client's Help Page:
```
./radar_internal.py -h
usage: RADAR Internal Command Client [-h]
                                     {info,distribute,playbook,collection-list,database-list,get-data,mission-list,mission-join,check-auth,grant-auth,remove-auth,document-commands}   
                                     ...

positional arguments:
  {info,distribute,playbook,collection-list,database-list,get-data,mission-list,mission-join,check-auth,grant-auth,remove-auth,document-commands}
                        Valid commands
    info                Get info about RADAR's state
    distribute          Run command on first available client
    playbook            Manually run playbook
    collection-list     List available collections
    database-list       List all databases and collections
    get-data            Read from any database and collection
    mission-list        List missions which have data
    mission-join        Change to another mission
    check-auth          Print authorization info
    grant-auth          Grant an API key authorization
    remove-auth         Remove an API key's authorization
    document-commands   Create a file containing all commands that were executed in the mission - great for documentation

optional arguments:
  -h, --help            show this help message and exit
```

In addition, `-h` is a usable flag to view the individual help for each command, including required and optional arguments (the ones surrounded by square brackets).

E.g.
```
./radar_internal.py get-data -h       
usage: RADAR Internal Command Client get-data [-h] -c COLLECTION [-d DATABASE]

optional arguments:
  -h, --help            show this help message and exit
  -c COLLECTION, --collection COLLECTION
                        Which collection to read
  -d DATABASE, --database DATABASE
                        Which database to read
```

For example to get the JSON data about the parsed target information (see `collection-list` if you want to see what's available) and then parse it using `jq` the command might look like the following:
```
./radar_internal.py get-data -c targets | jq '.'
```
