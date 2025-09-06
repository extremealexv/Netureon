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
            
        # Prioritize common ports first for faster profiling
        priority_ports = [80, 443, 22, 23]  # HTTP(S), SSH, Telnet
        iot_ports = [8080, 8443, 1883, 8883]  # HTTP(S), MQTT
        network_ports = [161, 162, 53, 67, 68]  # SNMP, DNS, DHCP
        media_ports = [554, 1935, 5353]  # RTSP, RTMP, mDNS
        
        # Combine all ports, remove duplicates, maintain priority order
        all_ports = (priority_ports + 
                    [p for p in ports if p not in priority_ports] +
                    iot_ports + network_ports + media_ports)
        all_ports = list(dict.fromkeys(all_ports))  # Remove duplicates while preserving order
        
        open_ports = []
        # Use multiple threads for faster scanning
        from concurrent.futures import ThreadPoolExecutor, as_completed
        from concurrent.futures import TimeoutError
        
        def check_port(port):
            try:
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                    sock.settimeout(0.2)  # Very short timeout for faster scanning
                    result = sock.connect_ex((self.ip_address, port))
                    if result == 0:
                        return port
                    return None
            except Exception:
                return None
        
        # Scan in parallel with a maximum of 10 concurrent checks
        with ThreadPoolExecutor(max_workers=10) as executor:
            future_to_port = {executor.submit(check_port, port): port 
                            for port in all_ports}
            
            for future in as_completed(future_to_port):
                try:
                    port = future.result(timeout=0.5)
                    if port is not None:
                        open_ports.append(port)
                except TimeoutError:
                    continue
                
        return sorted(open_ports)

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
