## Check Blocked IP Address

## Overview
The plugin is based on the IP zone HST, which the client is using an unauthorized IP address. The SYS requires the NET to assign this IP to a static MAC. So, SYS also needs to check whether the IP is blocked or not.

## Features
This plugin allows users to check if a specific IP address is blocked on a network device using SNMP. Users can input the IP gateway, SNMP community string, and the IP address they want to check. The plugin will then perform an SNMP query to determine if the IP address is blocked and display the results on the dashboard.

### Installation
1. Clone the plugin repository into the `plugins` directory of your Netbox instance.
```bash
cd /opt/netbox/
source /opt/netbox/venv/bin/activate
git clone https://github.com/anhntn98/check_blocked_ip.git check_blocked_ip
cd check_blocked_ip
pip install .
```
2. Add the plugin to the `PLUGINS` list in your Netbox configuration file
```bash
vi /opt/netbox/netbox/netbox/configuration.py
```
```python
PLUGINS = [
    ...
    'check_blocked_ip',
]
```

4. Restart the Netbox service to apply the changes.

```bash
sudo systemctl restart netbox
```



