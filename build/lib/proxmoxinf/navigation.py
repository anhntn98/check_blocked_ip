from netbox.plugins import PluginMenuItem
dashboard_menu_item = PluginMenuItem(
    link='plugins:proxmoxinf:dashboard',
    link_text='Dashboard',
    staff_only=True
)
list_menu_item = PluginMenuItem(
    link='plugins:proxmoxinf:auth_list',
    link_text='Proxmox Config',
    staff_only=True
)

menu_items = [dashboard_menu_item, list_menu_item]