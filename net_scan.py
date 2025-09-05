"""Network scanning module for Netureon.

This module provides network discovery and device tracking functionality using
ARP scanning and device profiling capabilities.
"""

import psycopg2
import netifaces
import asyncio
import time
from scapy.all import ARP, Ether, srp
from datetime import datetime
import ipaddress
import os
import logging
from dotenv import load_dotenv
from device_profiler import DeviceProfiler
from version import __version__
from webui.app import create_app
from webui.utils.email_notifier import EmailNotifier
from webui.utils.telegram_notifier import TelegramNotifier

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()
logger.info(f"Netureon Scanner v{__version__} initialized")

# PostgreSQL connection settings
DB_CONFIG = {
    'dbname': os.getenv('DB_NAME'),
    'user': os.getenv('DB_USER'),
    'password': os.getenv('DB_PASSWORD'),
    'host': os.getenv('DB_HOST'),
    'port': os.getenv('DB_PORT')
}

def get_local_subnet():
    """
    Detect and return the local subnet for network scanning.
    
    Returns:
        str: CIDR notation of the local subnet (e.g., '192.168.1.0/24')
        
    Raises:
        RuntimeError: If no active LAN interface with IPv4 is found
    """
    for iface in netifaces.interfaces():
        # Skip loopback and non-active interfaces
        if iface == 'lo' or not netifaces.AF_INET in netifaces.ifaddresses(iface):
            continue
        
        # Get IPv4 address and netmask
        ipv4_info = netifaces.ifaddresses(iface)[netifaces.AF_INET][0]
        ip = ipv4_info['addr']
        netmask = ipv4_info['netmask']
        
        # Convert IP and netmask to network address
        if ip and netmask:
            ip_interface = ipaddress.IPv4Interface(f"{ip}/{netmask}")
            network = ip_interface.network
            
            # Only return if it's a private network
            if network.is_private:
                return str(network)

    raise RuntimeError("No active LAN interface with IPv4 found.")

class NetworkScanner:
    def __init__(self):
        """Initialize the network scanner."""
        self.running = False
        self.email_notifier = EmailNotifier()
        self.telegram_notifier = TelegramNotifier()
        
    def start_monitoring(self):
        """Start the network monitoring loop."""
        self.running = True
        logger.info("Starting network monitoring...")
        
        while self.running:
            try:
                subnet = get_local_subnet()
                devices = self.scan_network(subnet)
                self._update_database(devices)
                time.sleep(int(os.getenv('SCAN_INTERVAL', 300)))  # Default 5 minutes
            except Exception as e:
                logger.error(f"Error in main loop: {str(e)}")
                time.sleep(60)  # Wait before retrying
                
    def scan_network(self, subnet):
        """
        Scan the network using ARP requests.
        
        Args:
            subnet (str): The subnet to scan in CIDR notation
            
        Returns:
            list: List of tuples containing (ip, mac) pairs
        """
        try:
            # Create ARP request packet
            arp = ARP(pdst=subnet)
            ether = Ether(dst="ff:ff:ff:ff:ff:ff")
            packet = ether/arp

            # Send packet and get responses
            result = srp(packet, timeout=3, verbose=0)[0]
            
            # Process responses
            devices = []
            for sent, received in result:
                devices.append((received.psrc, received.hwsrc))
                
            return devices
            
        except Exception as e:
            logger.error(f"Error scanning network: {str(e)}")
            return []
            
    def _update_database(self, devices):
        """
        Update the database with discovered devices.
        
        Args:
            devices (list): List of (ip, mac) tuples
        """
        try:
            conn = psycopg2.connect(**DB_CONFIG)
            cur = conn.cursor()
            
            for ip, mac in devices:
                # Skip localhost and broadcast
                if ip in ['127.0.0.1', '255.255.255.255'] or mac == 'ff:ff:ff:ff:ff:ff':
                    continue
                    
                # Profile the device
                profiler = DeviceProfiler(mac, ip)
                profile = profiler.profile()
                
                # Check if device exists
                cur.execute("""
                    SELECT id, last_seen, hostname, vendor
                    FROM devices 
                    WHERE mac_address = %s
                """, (mac,))
                
                result = cur.fetchone()
                now = datetime.now()
                
                if result:
                    device_id, last_seen, old_hostname, old_vendor = result
                    
                    # Update existing device
                    cur.execute("""
                        UPDATE devices 
                        SET ip_address = %s,
                            last_seen = %s,
                            hostname = %s,
                            vendor = %s,
                            open_ports = %s
                        WHERE id = %s
                    """, (
                        ip, 
                        now,
                        profile.get('hostname', old_hostname),
                        profile.get('vendor', old_vendor),
                        profile.get('open_ports', []),
                        device_id
                    ))
                    
                else:
                    # Insert new device
                    cur.execute("""
                        INSERT INTO devices (
                            mac_address, 
                            ip_address, 
                            first_seen,
                            last_seen,
                            hostname,
                            vendor,
                            open_ports
                        ) VALUES (%s, %s, %s, %s, %s, %s, %s)
                    """, (
                        mac,
                        ip,
                        now,
                        now,
                        profile.get('hostname', 'Unknown'),
                        profile.get('vendor', 'Unknown'),
                        profile.get('open_ports', [])
                    ))
                    
                    # Send notifications for new device
                    device_info = f"New device detected:\nMAC: {mac}\nIP: {ip}\nHostname: {profile.get('hostname', 'Unknown')}\nVendor: {profile.get('vendor', 'Unknown')}"
                    self.email_notifier.send_notification("New Device Detected", device_info)
                    self.telegram_notifier.send_message(device_info)
            
            conn.commit()
            
        except Exception as e:
            logger.error(f"Database error: {str(e)}")
            if conn:
                conn.rollback()
        finally:
            if cur:
                cur.close()
            if conn:
                conn.close()
