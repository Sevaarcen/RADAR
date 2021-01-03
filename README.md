# RADAR
Red-team Analysis, Documentation, and Automation Revolution

# Features
* Modular plugin support
* Integrates with your existing workflow


# Required System Components
* Python 3.6 or later
    * packages in requirements.txt
* Following system packages
    * yara
* A MongoDB server connected to the RADAR Control Server


# Wanted System Components
The following software components are not required, but are needed for full functionality (e.g. playbooks and commanders)

* nmap
* samba-common (for rpcclient)


# Self-signed certificate help
I used [this guide](https://medium.com/@tbusser/creating-a-browser-trusted-self-signed-ssl-certificate-2709ce43fd15)
to make my self-signed certificates for testing.
If you're using an IP address instead of a domain name, change the V3 ext file
as shown in [this guide](https://access.redhat.com/documentation/en-us/red_hat_enterprise_linux/6/html/deployment_guide/sssd-ldap-domain-ip)


# Data Format Specifications

### Target information
A valid target is json that has the following structure (see actual example below).
* `target_host`: REQUIRED - This key is the IP address, domain name, or hostname of the target. This must uniquely identify the device and be usable by programs which take this data as arguments (e.g. nmap).
* `source_command`: REQUIRED - This field is an internal UUID used by RADAR. This UUID can be queried in the database to find detailed information about the command that this target was parsed from.
* `details`: This optional key contains arbitrary metadata about the host - for example what type of device it is or how strong the network connection is to the device.
* `services`: This optional key contains a list of open ports on the host and information about the services it's running.
* `vulnerabilities`: This optional key contains a list of information about potential vulnerabilities the host has. This data is typically used by playbooks.

```json
{
  "target_host": "scanme.nmap.org",
  "details": {
    "host_type": "mailserver;webserver",
    "latency": "0.093",
    "scan_time": 1609632285,
    "status": "up",
    "value": "high"
  },
  "services": [
    {
      "port": "22",
      "protocol": "tcp",
      "service": "ssh",
      "state": "open"
    },
    {
      "port": "80",
      "protocol": "tcp",
      "service": "http",
      "state": "open"
    },
    {
      "port": "9929",
      "protocol": "tcp",
      "service": "nping-echo",
      "state": "open"
    },
    {
      "port": "31337",
      "protocol": "tcp",
      "service": "Elite",
      "state": "open"
    }
  ],
  "source_command": "ed73d874-7ad9-4343-a2e4-d9f17ddea966"
}
```
