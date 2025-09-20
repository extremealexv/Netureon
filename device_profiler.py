import nmap
import logging
import subprocess
import socket
from mac_vendor_lookup import MacLookup

class DeviceProfiler:
    def __init__(self):
        self.logger = logging.getLogger('netureon')
        self.nm = nmap.PortScanner()
        self.mac_lookup = MacLookup()

    def _run_nmap_scan(self, ip):
        """Run nmap scan with proper privileges."""
        try:
            # Try direct nmap execution first
            scan_result = self.nm.scan(
                ip,
                arguments='-sT -T4 -F -Pn'  # Use TCP connect scan which doesn't require root
            )
            return scan_result
        except Exception as e:
            self.logger.error(f"Port scan failed: {e}")
            return None

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
            
            # Get hostname
            self.logger.info("1. Resolving hostname...")
            try:
                profile['hostname'] = socket.gethostbyaddr(clean_ip)[0]
                self.logger.info(f"   • Hostname: {profile['hostname']}")
            except (socket.herror, socket.gaierror) as e:
                self.logger.info(f"   • Hostname: Unknown ({e})")

            # Get vendor
            self.logger.info("2. Looking up vendor...")
            try:
                profile['vendor'] = self.mac_lookup.lookup(mac)
                self.logger.info(f"   • Vendor found: {profile['vendor']}")
            except Exception as e:
                self.logger.info(f"   • Vendor lookup failed: {e}")

            # Scan ports
            self.logger.info("3. Scanning ports...")
            scan_result = self._run_nmap_scan(clean_ip)
            
            if scan_result:
                if isinstance(scan_result, str):
                    # Parse sudo nmap output
                    # ... parse the text output ...
                    self.logger.info("   • Scan completed using sudo")
                else:
                    # Handle python-nmap output
                    if clean_ip in self.nm.all_hosts():
                        host = self.nm[clean_ip]
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
            else:
                self.logger.warning("   • Port scan failed - no results")

            self.logger.info("=== Device profiling completed ===")
            return profile

        except Exception as e:
            self.logger.error(f"Device profiling failed: {str(e)}")
            return profile

    def _determine_device_type(self, port_numbers):
        """Determine device type based on open ports."""
        if 80 in port_numbers or 443 in port_numbers:
            return "Web Server"
        elif 8080 in port_numbers or 8443 in port_numbers:
            return "Web Service"
        elif 22 in port_numbers:
            return "SSH Server"
        elif 21 in port_numbers:
            return "FTP Server"
        elif 3306 in port_numbers:
            return "MySQL Database"
        elif 5432 in port_numbers:
            return "PostgreSQL Database"
        elif 1883 in port_numbers or 8883 in port_numbers:
            return "MQTT Device"
        elif 53 in port_numbers:
            return "DNS Server"
        else:
            return "Unknown"
