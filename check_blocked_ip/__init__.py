from netbox.plugins import PluginConfig


class CheckBlockedIpConfig(PluginConfig):
    name = 'check_blocked_ip'
    verbose_name = 'Check Blocked IP'
    description = 'Check blocked IP addresses'
    version = '0.1'
    base_url = 'check_blocked_ip'
    min_version = '3.4.0'


config = CheckBlockedIpConfig
