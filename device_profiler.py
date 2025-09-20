import nmap
import socket
import logging
from mac_vendor_lookup import MacLookup
import json

class DeviceProfiler:
    def __init__(self):
        self.logger = logging.getLogger('netureon')
        self.nm = nmap.PortScanner()
        self.mac_lookup = MacLookup()
        try:
            self.mac_lookup.update_vendors()
            self.logger.info("MAC vendor database updated successfully")
        except Exception as e:
            self.logger.warning(f"Could not update MAC vendor database: {e}")

    def profile_device(self, ip, mac):
        """Profile a device by IP and MAC address"""
        self.logger.info(f"Starting device profiling - IP: {ip}, MAC: {mac}")
        
        profile = {
            'hostname': 'Unknown',
            'vendor': 'Unknown',
            'device_type': 'Unknown',
            'open_ports': []
        }
        
        try:
            # Try to get hostname
            try:
                profile['hostname'] = socket.gethostbyaddr(ip)[0]
            except socket.herror:
                self.logger.debug(f"Could not resolve hostname for {ip}")

            # Try to get vendor from MAC
            try:
                profile['vendor'] = self.mac_lookup.lookup(mac)
                self.logger.info(f"Found vendor for {mac}: {profile['vendor']}")
            except Exception as e:
                self.logger.warning(f"Vendor lookup failed for MAC {mac}: {e}")

            # Scan for open ports
            try:
                scan_result = self.nm.scan(ip, arguments='-sS -sV -T4 -F --max-retries 2')
                if ip in self.nm.all_hosts():
                    host = self.nm[ip]
                    
                    ports = []
                    for proto in host.all_protocols():
                        for port in host[proto].keys():
                            service = host[proto][port]
                            if service['state'] == 'open':
                                ports.append({
                                    'port': port,
                                    'service': service.get('name', 'unknown'),
                                    'version': service.get('version', '')
                                })
                    
                    profile['open_ports'] = ports
                    
                    # Determine device type based on open ports
                    profile['device_type'] = self._determine_device_type(ports)
                    
                self.logger.info(f"Port scan complete for {ip}")
                
            except Exception as e:
                self.logger.error(f"Port scan failed for {ip}: {e}")

            return profile

        except Exception as e:
            self.logger.error(f"Device profiling failed for {ip}: {e}")
            return profile

    def _determine_device_type(self, ports):
        """Determine device type based on open ports"""
        port_numbers = [p['port'] for p in ports]
        services = [p['service'].lower() for p in ports]
        
        if 80 in port_numbers or 443 in port_numbers:
            if 3389 in port_numbers or 445 in port_numbers:
                return 'Windows PC'
            elif 22 in port_numbers:
                return 'Linux Server'
            return 'Web Server'
        elif 22 in port_numbers:
            if any(p in port_numbers for p in [161, 162, 23]):
                return 'Network Device'
            return 'Linux Device'
        elif 8080 in port_numbers or 8443 in port_numbers:
            return 'IoT Device'
        elif 5353 in port_numbers or 5000 in port_numbers:
            return 'Smart Device'
        return 'Unknown'
