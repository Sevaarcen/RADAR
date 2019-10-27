# RADAR
Red-team Analysis, Documentation, and Automation Revolution

# Features
* Modular plugin support
* Integrates with your existing workflow

# Requirements
* Python 3.6 or later
    * packages in requirements.txt
    
# Example generating self-signed certificates
```bash
openssl req -x509 -newkey rsa:4096 -keyout key.pem -out cert.pem -days 365 -extensions v3_req
```
```bash
openssl req -x509 -new -nodes -key key.pem -sha256 -days 365 -out rootCA.crt
```

# Data Format Specifications
### Target information
Target_host is the primary key. Other fields are optional. "services" must contain JSON formatted as shown below to work with the Playbooks.
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