import nmap
import socket
import requests
import logging
from mac_vendor_lookup import MacLookup
from concurrent.futures import ThreadPoolExecutor

class DeviceProfiler:
    def __init__(self):
        self.logger = logging.getLogger('netureon')
        self.nm = nmap.PortScanner()
        self.mac_lookup = MacLookup()
        # Update MAC vendor database
        try:
            self.mac_lookup.update_vendors()
        except Exception as e:
            self.logger.warning(f"Could not update MAC vendor database: {e}")

    def profile_device(self, ip, timeout=5):
        """Profile a device by IP address"""
        try:
            self.logger.info(f"Profiling device at {ip}")
            profile = {
                'hostname': self._get_hostname(ip),
                'vendor': None,
                'device_type': None,
                'open_ports': []
            }

            # Scan common ports
            try:
                result = self.nm.scan(ip, arguments=f'-sV -sT -T4 --min-rate 1000 --max-retries 2 --host-timeout {timeout}s')
                if ip in self.nm.all_hosts():
                    host_data = self.nm[ip]
                    
                    # Get open ports
                    profile['open_ports'] = []
                    for proto in host_data.all_protocols():
                        ports = host_data[proto].keys()
                        for port in ports:
                            service = host_data[proto][port]
                            if service['state'] == 'open':
                                profile['open_ports'].append({
                                    'port': port,
                                    'service': service.get('name', 'unknown'),
                                    'version': service.get('version', '')
                                })

                    # Try to determine device type
                    profile['device_type'] = self._determine_device_type(profile['open_ports'])
            except Exception as e:
                self.logger.error(f"Port scan failed for {ip}: {e}")

            # Get MAC vendor information
            if hasattr(self.nm, 'all_hosts_mac'):
                mac = self.nm.all_hosts_mac().get(ip)
                if mac:
                    try:
                        profile['vendor'] = self.mac_lookup.lookup(mac)
                    except Exception as e:
                        self.logger.warning(f"Vendor lookup failed for MAC {mac}: {e}")

            self.logger.info(f"Profile complete for {ip}: {profile}")
            return profile

        except Exception as e:
            self.logger.error(f"Device profiling failed for {ip}: {e}")
            return None

    def _get_hostname(self, ip):
        """Get hostname for IP address"""
        try:
            return socket.gethostbyaddr(ip)[0]
        except:
            return None

    def _determine_device_type(self, open_ports):
        """Determine device type based on open ports"""
        ports = [p['port'] for p in open_ports]
        services = [p['service'].lower() for p in open_ports]

        if 80 in ports or 443 in ports:
            if any(s in services for s in ['microsoft-ds', 'netbios']):
                return 'Windows PC'
            elif 'ssh' in services:
                return 'Linux/Unix Device'
            else:
                return 'Web Server'
        elif 22 in ports:
            return 'Network Device'
        elif 8080 in ports or 8443 in ports:
            return 'IoT Device'
        elif 161 in ports or 162 in ports:
            return 'Network Equipment'
        else:
            return 'Unknown'
