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
        
    def _get_hostname(self, ip):
        """Get hostname for IP with error handling."""
        try:
            # Remove subnet mask if present
            clean_ip = ip.split('/')[0]
            return socket.gethostbyaddr(clean_ip)[0]
        except (socket.herror, socket.gaierror) as e:
            self.logger.debug(f"Could not resolve hostname for {ip}: {e}")
            return "Unknown"
        except Exception as e:
            self.logger.error(f"Error resolving hostname for {ip}: {e}")
            return "Unknown"

    def profile_device(self, ip, mac):
        """Profile a device by IP and MAC address."""
        self.logger.info(f"\n=== Starting device profiling for {ip} ({mac}) ===")
        
        profile = {
            'hostname': 'Unknown',
            'vendor': 'Unknown',
            'device_type': 'Unknown',
            'open_ports': []
        }
        
        try:
            # Clean IP address if it has subnet mask
            clean_ip = ip.split('/')[0]
            
            self.logger.info("1. Resolving hostname...")
            profile['hostname'] = self._get_hostname(clean_ip)
            self.logger.info(f"   • Hostname: {profile['hostname']}")

            # Try to get vendor from MAC
            self.logger.info("2. Looking up vendor...")
            try:
                profile['vendor'] = self.mac_lookup.lookup(mac)
                self.logger.info(f"   • Vendor found: {profile['vendor']}")
            except Exception as e:
                self.logger.info(f"   • Vendor lookup failed: {e}")

            # Scan for open ports with sudo
            self.logger.info("3. Scanning ports...")
            try:
                # Use sudo for nmap scan
                scan_result = self.nm.scan(
                    ip, 
                    arguments='-sS -sV -T4 -F --max-retries 2',
                    sudo=True
                )
                if ip in self.nm.all_hosts():
                    host = self.nm[ip]
                    
                    for proto in host.all_protocols():
                        for port in host[proto].keys():
                            service = host[proto][port]
                            if service['state'] == 'open':
                                port_info = {
                                    'port': port,
                                    'service': service.get('name', 'unknown'),
                                    'version': service.get('version', '')
                                }
                                profile['open_ports'].append(port_info)
                                self.logger.info(f"   • Found open port: {port} ({service.get('name', 'unknown')})")
                    
                    # Determine device type
                    profile['device_type'] = self._determine_device_type(profile['open_ports'])
                    self.logger.info(f"   • Determined device type: {profile['device_type']}")
                
            except Exception as e:
                self.logger.error(f"   • Port scan failed: {e}")
                # Still continue with partial profile

            self.logger.info("=== Device profiling completed ===")
            return profile

        except Exception as e:
            self.logger.error(f"Device profiling failed: {e}")
            return profile

    def _determine_device_type(self, ports):
        """Determine device type based on open ports"""
        port_numbers = [p['port'] for p in ports]
        services = [p['service'].lower() for p in ports]
        
        if 80 in port_numbers or 443 in port_numbers:
            if 3389 in port_numbers or 445 in port_numbers:
                return 'Windows PC'
            return 'Linux Device'
        elif 8080 in port_numbers or 8443 in port_numbers:
            return 'IoT Device'
        elif 5353 in port_numbers or 5000 in port_numbers:
            return 'Smart Device'
        return 'Unknown'
