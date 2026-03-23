from netbox.plugins import PluginMenuItem
dashboard_menu_item = PluginMenuItem(
    link='plugins:check_blocked_ip:dashboard',
    link_text='Dashboard',
    staff_only=True
)


menu_items = [dashboard_menu_item]