# Getting Started

Once you have RADAR on your central host, the first step is to setup the RADAR control server where clients connect and send data.


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

1. Generate certificates to allow the website to use HTTPS
2. Allow port through firewall
    ```
    sudo firewall-cmd --add-port=1794/tcp --permanent
    sudo firewall-cmd --reload
    ```
3. Start a Mongo Database. The root account should match the credentials in ```server_config.toml```. Using podman this could look like:
    ```
    sudo podman run -d --name radar_database -p 27017:27017 -e MONGO_INITDB_ROOT_USERNAME=root -e MONGO_INITDB_ROOT_PASSWORD=R4d4rD4t4b4s3 mongo:latest
    ```
4. Start the RADAR Control Server using the ```server.py``` script
5. Keep the console open, closing the script will shutdown the server


# Steps to Setup RADAR Uplink Server

A RADAR Uplink Server is a server which runs on every host which has a RADAR Client. This server's job is to manage communication between the client and server and offload responsibility from the client so it runs as quickly as possible.

1. Copy your root CA public key to the file path specified in ```uplink_config.toml```. By default this is a file called ```rootCA.pem`` in the RADAR base directory.
2. Ensure the ```host``` key in the config file exactly matches the CN of the certificate.
3. Start the RADAR Uplink Server using the ```uplink_server.py``` script.
4. Keep the console open, closing the script will shutdown the server


# Steps to Setup RADAR Client

A RADAR Client's purpose is to ingest system command output and provide an interface to manage the RADAR environment.

1. Ensure your local RADAR Uplink server is running.
