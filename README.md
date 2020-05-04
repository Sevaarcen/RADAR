# RADAR
Red-team Analysis, Documentation, and Automation Revolution

# Features
* Modular plugin support
* Integrates with your existing workflow

# Requirements
* Python 3.6 or later
    * packages in requirements.txt
* Following system packages
    * yara
    * samba-common (for rpcclient)
* A MongoDB server connected to the RADAR Control Server
    
# Self-signed certificate help
I used [this guide](https://medium.com/@tbusser/creating-a-browser-trusted-self-signed-ssl-certificate-2709ce43fd15)
to make my self-signed certificates for testing.
If you're using an IP address instead of a domain name, change the V3 ext file
as shown in [this guide](https://access.redhat.com/documentation/en-us/red_hat_enterprise_linux/6/html/deployment_guide/sssd-ldap-domain-ip)

# Data Format Specifications
### Target information
Target_host is the primary key. Other fields are optional.
"services" must contain JSON formatted as shown below to work with the Playbooks.
```json
{
  "target_host": "scanme.nmap.org",
  "details": {
    "value": "low",
    "last_scan": "1572142040.0714252",
    "latency": 0.10
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
    }
  ]
}
```
