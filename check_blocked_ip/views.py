from django.db.models import Count
from django.http import JsonResponse
from django.shortcuts import redirect, render
from netbox.views import generic
from proxmoxer import ProxmoxAPI
import time
from django.conf import settings
from django.core.mail import EmailMessage
from datetime import datetime, timezone, timedelta
import re
from django.views import View
import logging
import json
import os
import subprocess
import ipaddress


logger = logging.getLogger(__name__)

def snmpwalk(COMMUNITY,ip_gw, oid, index=None,ip=None):
        cmd = 'snmpwalk -v2c -c {} -Oq {} {} | grep ""'.format(COMMUNITY, ip_gw, oid,ip)
        if index: cmd = f'{cmd}.{index}'
        for _ in range(2):
            gets = subprocess.run(cmd, shell=True, stdout = subprocess.PIPE, stderr = subprocess.PIPE)
            if gets.returncode == 0:
                try:
                    return gets.stdout.decode("cp932")
                except Exception as e:
                    logger.exception(e)
                    return gets.stdout
            return {2:gets.stderr}
        return None


def is_valid_ip(ip_string):
    """
    Checks if the provided string is a valid IPv4 or IPv6 address.
    Returns True if valid, False otherwise.
    """
    try:
        ipaddress.ip_address(ip_string)
        return True
    except ValueError:
    # A ValueError is raised if the address is invalid
        return False



class DashBoard(View):
    
    OID_typeMac = '1.3.6.1.2.1.4.22.1.4'
    template_name = "check_blocked_ip/dashboard.html"

    # get method to render the dashboard template
    def get(self, request):
               
        return render(
            request,
            self.template_name,
        )

    # post method to handle the form submission and get VM information from Proxmox API
    def post(self, request):

        ip = request.POST.get("ip_address", "")
        community = request.POST.get("community", "")
        ipgw = request.POST.get("ipgw", "")

        if ip and community and ipgw:
            ip = ip.strip()
            community = community.strip()
            ipgw = ipgw.strip()
            if is_valid_ip(ip) and is_valid_ip(ipgw):            
                res = snmpwalk(community,ipgw,self.OID_typeMac,ip)
                if res is None:
                    return render(
                        request,
                        self.template_name,
                        {
                            "message": f'Can not IP {ip} on gateway {ipgw}.',
                            "ipgw" : ipgw,
                            "community" : community,
                            "ip" : ip
                        },
                    )
                if type(res) is dict:
                    return render(
                        request,
                        self.template_name,
                        {
                            "error": res[2] or f"Please check all inputs and try again.",
                            "ipgw" : ipgw,
                            "community" : community,
                            "ip" : ip
                        },
                    )
                type_mac=str(res.splitlines()[0].split()[-1])
                if "static" in type_mac:
                    return render(
                        request,
                        self.template_name,
                        {
                            "message": f'IP {ip} is BLOCKED',
                            "ipgw" : ipgw,
                            "community" : community,
                        },
                    )

                else:
                    return render(
                        request,
                        self.template_name,
                        {
                            "message": f'IP {ip} is NOT BLOCKED',
                            "ipgw" : ipgw,
                            "community" : community,
                        },
                    )     
            
            else:
                return render(
                    request,
                    self.template_name,
                    {
                        "error": f'Please enter a valid IP address.',
                    },
                )
        else:
            return render(
                    request,
                    self.template_name,
                    {
                        "error": f'Please enter all required fields.',
                    },
                )
            




    