from netbox.plugins import PluginConfig


class ProxmoxInfConfig(PluginConfig):
    name = 'proxmoxinf'
    verbose_name = ' Proxmox Inf'
    description = 'Get Proxmox VM information'
    version = '0.1'
    base_url = 'proxmoxinf'
    min_version = '3.4.0'


config = ProxmoxInfConfig
