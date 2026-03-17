from django.db.models import Count
from django.http import JsonResponse
from django.shortcuts import redirect, render
from netbox.views import generic
from proxmoxer import ProxmoxAPI
import time
from django.conf import settings
from virtualization.models import Cluster, VirtualMachine, VMInterface
from django.core.mail import EmailMessage
from datetime import datetime, timezone, timedelta
import re
from django.views import View
import logging
import proxmoxer
import json
import os

logger = logging.getLogger(__name__)

PRX_CONFIG_PATH = "/opt/netbox/netbox/scripts/prxtonb/proxmox_config.json"


def load_config():
    """Load runtime config from JSON file."""
    if os.path.exists(PRX_CONFIG_PATH):
        with open(PRX_CONFIG_PATH) as f:
            return json.load(f)
    return {}


def save_config(data):
    """Overwrite config file with updated dict."""
    with open(PRX_CONFIG_PATH, "w") as f:
        json.dump(data, f, indent=4)


def get_nodes(request, cluster):
    logger.info(f"Received request to get nodes for cluster: {cluster}")
    PROXMOX_CONFIG = load_config()
    nodes = []
    if cluster in PROXMOX_CONFIG:
        config = PROXMOX_CONFIG[cluster]
        try:
            proxmox = ProxmoxAPI(
                config["host_ip"],
                user=config["username"],
                password=config["password"],
                port=config.get("port", "8006"),
                verify_ssl=False,
            )
            nodess = proxmox.nodes.get()
            if nodess:
                nodes = [node["node"] for node in nodess]
            else:
                nodes = []
        except Exception as e:
            nodes = []
    logger.info(f"Returning nodes for cluster {cluster}: {nodes}")

    return JsonResponse(nodes, safe=False)


class DashBoard(View):

    template_name = "proxmoxinf/dashboard.html"
    PROXMOX_CONFIG = load_config()
    cluster_list = list(PROXMOX_CONFIG.keys()) if PROXMOX_CONFIG else None

    # get method to render the dashboard template
    def get(self, request):
        

        if self.cluster_list:
            return render(
                request,
                self.template_name,
                {"cluster_list": self.cluster_list,}
                )
        
        return render(
            request,
            self.template_name,
            {"error": "No cluster configuration found. Please add a cluster configuration first."},
        )

    # post method to handle the form submission and get VM information from Proxmox API
    def post(self, request):
        logger.info("Received POST request with data: %s", request.POST)
        # Extract form data
        vmid = request.POST.get("vmid", "")
        cluster = request.POST.get("cluster", "")
        node = request.POST.get("node", "")

        if vmid and cluster and node:
            vmid = int(vmid)
            try:
                # Check if the cluster exists in NetBox
                clst = Cluster.objects.get(name=cluster)
            except Exception as e:
                logger.warning(f'Cluster "{cluster}" not found in NetBox: {e}')
                return render(
                    request,
                    self.template_name,
                    {
                        "error": f'Cluster "{cluster}" not found in NetBox. Please check your data.',
                        "cluster_list": self.cluster_list,
                    },
                    
                )
            # Get Proxmox API configuration from plugin settings
            PROXMOX_CONFIG = load_config()
            if PROXMOX_CONFIG and cluster in PROXMOX_CONFIG:
                cluster_config = PROXMOX_CONFIG[cluster]

                if (
                    cluster_config["host_ip"]
                    and cluster_config["username"]
                    and cluster_config["password"]
                    and cluster_config["bkstorage_name"]
                    and cluster_config["port"]
                ):
                    # Connect to Proxmox API
                    proxmox = ProxmoxAPI(
                        cluster_config["host_ip"],
                        user=cluster_config["username"],
                        password=cluster_config["password"],
                        port = cluster_config["port"],
                        verify_ssl=False,
                    )
                    try:
                        # Get VM information from Proxmox API
                        statuss = proxmox.nodes(node).qemu(vmid).status.current.get()
                    except Exception as e:
                        return render(
                            request,
                            self.template_name,
                            {
                                "error": f"Please check your Proxmox configuration and VM ID.",
                                "cluster_list": self.cluster_list,
                            },
                        )
                    vm_name = ""
                    status = ""
                    start_on_boot = ""
                    listinf = {vmid: {}}
                    if statuss:
                        vm_name = statuss.get("name", "")
                        status = statuss.get("status", "")
                    config = proxmox.nodes(node).qemu(vmid).config.get()
                    if config:
                        start_on_boot = config.get("onboot", "")
                        if status == "running":
                            for key, value in config.items():
                                if (key.startswith("net")) and (
                                    "link_down=1" not in value
                                ):
                                    listinf[int(vmid)][key] = value
                    scheduled_backups = proxmox.cluster.backup.get()
                    schd = ""
                    count = 0
                    ctime = ""
                    ha_status = ""
                    if scheduled_backups:
                        for backup in scheduled_backups:
                            if str(vmid) in backup["vmid"]:
                                if schd:
                                    schd += ", "
                                schd += backup["schedule"]

                        ha_vm = proxmox.cluster.ha.status.current.get()
                        if ha_vm:
                            ha_status = next(
                                (
                                    item["state"]
                                    for item in ha_vm
                                    if str(vmid) in item.get("sid", "")
                                ),
                                "unknown",
                            )
                        backups = (
                            proxmox.nodes(node)
                            .storage(cluster_config["bkstorage_name"])
                            .content.get()
                        )

                        if backups:
                            for backup in backups:
                                if int(backup["vmid"]) == int(vmid):
                                    count += 1
                                    if not ctime or backup["ctime"] > ctime:
                                        ctime = backup["ctime"]
                    try:
                        # Update or create the VM information in NetBox
                        a, created = VirtualMachine.objects.update_or_create(
                            cluster=clst,
                            custom_field_data__proxmox_id=vmid,
                            defaults={
                                "name": vm_name,
                                "status": (
                                    "active" if status == "running" else "offline"
                                ),
                            },
                        )
                        a.custom_field_data["proxmox_id"] = vmid
                        a.custom_field_data["prx_ha"] = ha_status
                        a.custom_field_data["proxmox_sob"] = start_on_boot
                        a.custom_field_data["prx_count_backup"] = count
                        a.custom_field_data["proxmox_node"] = node
                        tz = timezone(timedelta(hours=7))
                        dt = datetime.fromtimestamp(ctime, tz) if ctime else ""
                        a.custom_field_data["prx_latest_backup"] = (
                            dt.strftime("%Y-%m-%d %H:%M:%S") if dt else ""
                        )
                        a.custom_field_data["proxmox_bk_schedule"] = schd
                        a.snapshot()
                        a.save()
                    except Exception as e:
                        return render(
                            request,
                            self.template_name,
                            {
                                "error": f"Error updating VM information: {str(e)}. Please check your data and try again.",
                                "cluster_list": self.cluster_list,
                            },
                        )
                    # If the VM has network interfaces, update or create them in NetBox
                    if listinf:
                        VMinfs = []
                        for key, value in listinf.items():
                            try:
                                vm = VirtualMachine.objects.get(
                                    cluster=clst, custom_field_data__proxmox_id=key
                                )
                                for net, va in value.items():
                                    des_match = re.search(r"bridge=([^,]+)", va)
                                    des = des_match.group(1) if des_match else ""
                                    print(des)
                                    VMinfs.append(
                                        {
                                            "name": net,
                                            "virtual_machine": vm,
                                            "description": des,
                                        }
                                    )
                            except Exception as e:
                                logger.warning(
                                    f"Error processing VM interfaces for VM ID {key}: {e}"
                                )

                        if VMinfs:
                            for v in VMinfs:
                                try:
                                    VMInterface.objects.update_or_create(
                                        name=v["name"],
                                        virtual_machine=v["virtual_machine"],
                                        defaults={"description": v["description"]},
                                    )
                                except Exception as e:
                                    return render(
                                        request,
                                        self.template_name,
                                        {
                                            "error": f"Error updating VM interfaces: {str(e)}. Please check your data and try again.",
                                            "cluster_list": self.cluster_list,
                                        },
                                    )

                    return render(
                        request,
                        self.template_name,
                        {
                            "success_message": f'VM "{vm_name}" information updated successfully.',
                            "cluster_list": self.cluster_list,
                        },
                    )
                else:
                    return render(
                        request,
                        self.template_name,
                        {
                            "error": "Incomplete cluster configuration. Please check your settings.",
                            "cluster_list": self.cluster_list,
                        },
                    )
            else:
                return render(
                    request,
                    self.template_name,
                    {
                        "error": "Cluster configuration not found. Please check your settings.",
                        "cluster_list": self.cluster_list,
                    },
                )

        else:
            return render(
                request,
                self.template_name,
                {"error": "Please provide all required fields.", "cluster_list": self.cluster_list},
            )


class ProxmoxAuthList(View):

    template_name = "proxmoxinf/auth_list_add.html"
    cluster_list = Cluster.objects.filter(type__name="Proxmox").values_list(
        "name", flat=True
    )

    # get method to render the authentication template
    def get(self, request):
        try:
            logger.info("Loading Proxmox configuration for GET request")
            PROXMOX_CONFIG = load_config()
        except Exception as e:
            logger.error(f"Error loading Proxmox configuration: {e}")

        return render(
            request,
            self.template_name,
            {"proxmox_list": PROXMOX_CONFIG, "cluster_list": self.cluster_list},
        )

    # post method to handle the form submission and authenticate with Proxmox API
    def post(self, request):

        logger.info("Received POST request with data: %s", request.POST)
        # Extract form data
        cluster = request.POST.get("cluster", "")
        host_ip = request.POST.get("host_ip", "")
        username = request.POST.get("username", "")
        password = request.POST.get("password", "")
        bkstorage_name = request.POST.get("bkstorage_name", "")
        port = request.POST.get("port", "8006") or "8006"

        PROXMOX_CONFIG = load_config()
        if cluster and username and password and bkstorage_name and host_ip:
            if PROXMOX_CONFIG and cluster in PROXMOX_CONFIG:
                return render(
                    request,
                    self.template_name,
                    {
                        "proxmox_list": PROXMOX_CONFIG,
                        "cluster_list": self.cluster_list,
                        "error": "Cluster configuration already exists. Please choose a different cluster name.",
                        "cluster": cluster,
                        "username": username,
                        "password": password,
                        "bkstorage_name": bkstorage_name,
                        "port": port,
                    },
                )
            else:
                PROXMOX_CONFIG[cluster] = {
                    "host_ip": host_ip,
                    "username": username,
                    "password": password,
                    "bkstorage_name": bkstorage_name,
                    "port": port,
                }
                try:
                    ProxmoxAPI(
                        host_ip, user=username, password=password, verify_ssl=False
                    )
                except Exception as e:
                    del PROXMOX_CONFIG[cluster]
                    return render(
                        request,
                        self.template_name,
                        {
                            "proxmox_list": PROXMOX_CONFIG,
                            "cluster_list": self.cluster_list,
                            "error": f"Failed to connect to Proxmox API: {str(e)}. Please check your configuration.",
                            "cluster": cluster,
                            "username": username,
                            "password": password,
                            "bkstorage_name": bkstorage_name,
                            "port": port,
                            "host_ip": host_ip,
                        },
                    )

                save_config(PROXMOX_CONFIG)

                return render(
                    request,
                    self.template_name,
                    {
                        "proxmox_list": PROXMOX_CONFIG,
                        "cluster_list": self.cluster_list,
                        "success_message": f'Cluster "{cluster}" configuration added successfully.',
                    },
                )
        else:
            return render(
                request,
                self.template_name,
                {
                    "proxmox_list": PROXMOX_CONFIG,
                    "cluster_list": self.cluster_list,
                    "error": "Please provide all required fields.",
                    "cluster": cluster,
                    "username": username,
                    "password": password,
                    "bkstorage_name": bkstorage_name,
                    "host_ip": host_ip,
                    "port": port,
                },
            )


class ProxmoxAuthEdit(View):
    template_name = "proxmoxinf/auth_edit.html"

    def get(self, request, cluster):
        PROXMOX_CONFIG = load_config()
        if cluster in PROXMOX_CONFIG:
            config = PROXMOX_CONFIG[cluster]
            return render(
                request,
                "proxmoxinf/auth_edit.html",
                {"config": config, "cluster": cluster},
            )
        else:
            return redirect("auth_list")

    def post(self, request, cluster):
        logger.info(
            'Received POST request for editing cluster "%s" with data: %s',
            cluster,
            request.POST,
        )
        host_ip = request.POST.get("host_ip", "")
        username = request.POST.get("username", "")
        password = request.POST.get("password", "")
        bkstorage_name = request.POST.get("bkstorage_name", "")
        port = request.POST.get("port", "8006")
        PROXMOX_CONFIG = load_config()
        if cluster in PROXMOX_CONFIG:
            if host_ip and username and password and bkstorage_name:
                PROXMOX_CONFIG[cluster] = {
                    "host_ip": host_ip,
                    "username": username,
                    "password": password,
                    "bkstorage_name": bkstorage_name,
                    "port": port,
                }
                try:
                    ProxmoxAPI(
                        host_ip,
                        user=username,
                        password=password,
                        port=port,
                        verify_ssl=False,
                    )
                except Exception as e:
                    return render(
                        request,
                        self.template_name,
                        {
                            "config": PROXMOX_CONFIG[cluster],
                            "error": f"Failed to connect to Proxmox API: {str(e)}. Please check your configuration.",
                            "cluster": cluster,
                        },
                    )
                save_config(PROXMOX_CONFIG)
                return redirect("plugins:proxmoxinf:auth_list")
            else:
                return render(
                    request,
                    self.template_name,
                    {
                        "config": PROXMOX_CONFIG[cluster],
                        "error": "Please provide all required fields.",
                        "cluster": cluster,
                    },
                )
        else:
            return redirect("plugins:proxmoxinf:auth_list")


class ProxmoxAuthDelete(View):
    def post(self, request, cluster):
        # logger.info(f"Received request to delete cluster configuration: {cluster}")
        PROXMOX_CONFIG = load_config()
        if cluster in PROXMOX_CONFIG:
            del PROXMOX_CONFIG[cluster]
            save_config(PROXMOX_CONFIG)
            logger.info(f'Cluster configuration "{cluster}" deleted successfully.')
            return redirect("plugins:proxmoxinf:auth_list")
        else:
            logger.warning(f'Cluster configuration "{cluster}" not found for deletion.')
            return redirect("plugins:proxmoxinf:auth_list")
