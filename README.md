## Sync VM's information from Proxmox to Netbox

### Overview
This plugin allows you to sync VM's information from Proxmox to Netbox. It provides a dashboard where you can input the VM ID, Node, and Cluster to fetch the latest information about the VM and update it in Netbox. 
### Features
- Fetch VM information from Proxmox using the Proxmox API.
- Update VM information in Netbox, including custom fields for Proxmox ID and backup schedule.

### Usage
1. Install the plugin in your Netbox instance.
2. Navigate to the Proxmox Information Dashboard.
3. Enter the VM ID, Node, and Cluster information.
4. Click the "Get VM Information" button to fetch and update the VM information in Netbox.
5. The dashboard will display success or error messages based on the outcome of the operation.

### Error Handling
The plugin includes error handling to catch exceptions that may occur during the update process. If an error occurs, a user-friendly error message will be displayed on the dashboard, prompting the user to check their data and try again.

### Installation
To install the plugin, follow these steps:
Note: Make sure to custom fields are created in NetBox before using the plugin, you can create them in NetBox with the following names:
- proxmox_id (Integer)
- proxmox_bk_schedule (Text)
- prx_ha (Text)
- prx_count_backup (Integer)
- prx_latest_backup (Text)
- prx_bk_schedule (Text)
- proxmox_sob (Boolean)
1. Clone the plugin repository into the `plugins` directory of your Netbox instance.
```bash
cd /opt/netbox/
source /opt/netbox/venv/bin/activate
git clone https://github.com/anhntn98/proxmoxinf.git proxmoxinf
cd proxmoxinf
pip install -r requirements.txt
pip install .
```
2. Add the plugin to the `PLUGINS` list in your Netbox configuration file
```bash
vi /opt/netbox/netbox/netbox/configuration.py
```
```python
PLUGINS = [
    ...
    'proxmoxinf',
]
```
3. Check the plugin configuration and make sure to set the correct Proxmox information, username, and password in the `configuration.py` file of the plugin.
```python

PLUGINS_CONFIG = {
    ...
    'proxmox': {
        'name_cluster': 
        {
            'host': 'your_proxmox_host',
            'username': 'your_proxmox_username',
            'password': 'your_proxmox_password',
            'pbs': "your_proxmox_backup_server",
        }
    }
    ...

}
```


4. Restart the Netbox service to apply the changes.

```bash
sudo systemctl restart netbox
```

