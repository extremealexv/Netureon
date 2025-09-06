import socket
import requests
import subprocess
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

class DeviceProfiler:
    def __init__(self, mac_address, ip_address=None):
        self.mac_address = mac_address
        self.ip_address = ip_address

    def get_mac_vendor(self):
        url = f"https://api.macvendors.com/{self.mac_address}"
        try:
            response = requests.get(url, timeout=5)
            if response.status_code == 200:
                return response.text
            else:
                return "Unknown vendor"
        except Exception as e:
            return f"Error: {e}"

    def get_hostname(self):
        if not self.ip_address:
            return "IP address not provided"
        try:
            return socket.gethostbyaddr(self.ip_address)[0]
        except socket.herror:
            return "Hostname not found"

    def scan_open_ports(self, ports=[22, 23, 80, 443, 3389, 8080, 3306, 5432, 6379, 27017, 5000, 8000, 8888]):
        if not self.ip_address:
            return "IP address not provided"
        open_ports = []
        for port in ports:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.settimeout(1)
                result = sock.connect_ex((self.ip_address, port))
                if result == 0:
                    open_ports.append(port)
        return open_ports

    def profile(self):
        vendor = self.get_mac_vendor()
        hostname = self.get_hostname()
        open_ports = self.scan_open_ports()
        return {
            'mac_address': self.mac_address,
            'ip_address': self.ip_address,
            'vendor': vendor,
            'hostname': hostname,
            'open_ports': open_ports
        }
