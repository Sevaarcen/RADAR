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