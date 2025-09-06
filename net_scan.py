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

import signal
import fcntl
import sys
import os.path
import socket
import sdnotify

class NetworkScanner:
    def __init__(self):
        """Initialize the network scanner."""
        self.running = False
        self.app = create_app()
        self.email_notifier = EmailNotifier()
        self.telegram_notifier = TelegramNotifier()
        self.lock_file = '/tmp/netureon_scanner.lock'
        self.notifier = sdnotify.SystemdNotifier()
        
        # Setup signal handlers
        signal.signal(signal.SIGTERM, self.handle_shutdown)
        signal.signal(signal.SIGINT, self.handle_shutdown)
        
        # Notify systemd we're starting up
        self.notifier.notify("STATUS=Initializing...")
        
    def acquire_lock(self):
        """Try to acquire the lock file to prevent multiple instances."""
        try:
            self.lock_fd = open(self.lock_file, 'w')
            fcntl.lockf(self.lock_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            self.lock_fd.write(str(os.getpid()))
            self.lock_fd.flush()
            # Notify systemd we've acquired the lock
            self.notifier.notify("STATUS=Lock acquired")
            return True
        except IOError:
            logger.error("Another instance is already running")
            self.notifier.notify("STATUS=Failed to acquire lock")
            return False
            
    def release_lock(self):
        """Release the lock file."""
        try:
            if hasattr(self, 'lock_fd') and not self.lock_fd.closed:
                try:
                    fcntl.lockf(self.lock_fd, fcntl.LOCK_UN)
                except IOError:
                    pass
                self.lock_fd.close()
            
            if os.path.exists(self.lock_file):
                try:
                    os.unlink(self.lock_file)
                except OSError:
                    pass
        except Exception as e:
            logger.error(f"Error releasing lock: {e}")
            
    def handle_shutdown(self, signum, frame):
        """Handle shutdown signals gracefully."""
        logger.info("Received shutdown signal, cleaning up...")
        self.notifier.notify("STATUS=Shutting down...")
        self.running = False
        # Close any open database connections
        if hasattr(self, '_db_conn') and self._db_conn:
            try:
                self._db_conn.close()
            except:
                pass
        # Release the lock file
        self.release_lock()
        logger.info("Scanner shutdown complete")
        self.notifier.notify("STOPPING=1")
        # Exit immediately but cleanly
        sys.exit(0)
        
    def start_monitoring(self):
        """Start the network monitoring loop."""
        if not self.acquire_lock():
            logger.error("Failed to acquire lock. Another instance may be running.")
            self.notifier.notify("STATUS=Failed to start - lock exists")
            sys.exit(1)
            
        # Notify systemd we're ready
        self.notifier.notify("READY=1")
        self.notifier.notify("STATUS=Starting network monitoring...")
        logger.info("Starting network monitoring...")
            
        try:
            self.running = True
            logger.info("Starting network monitoring...")
            
            # Do initial scan immediately
            try:
                subnet = get_local_subnet()
                devices = self.scan_network(subnet)
                self._update_database(devices)
            except Exception as e:
                logger.error(f"Initial scan failed: {str(e)}")
            
            # Then enter the monitoring loop
            while self.running:
                try:
                    time.sleep(int(os.getenv('SCAN_INTERVAL', 300)))  # Default 5 minutes
                    if not self.running:
                        break
                    subnet = get_local_subnet()
                    devices = self.scan_network(subnet)
                    self._update_database(devices)
                except Exception as e:
                    logger.error(f"Error in main loop: {str(e)}")
                    if self.running:
                        time.sleep(60)  # Wait before retrying
        finally:
            self.release_lock()
                
    def scan_network(self, subnet):
        """
        Scan the network using ARP requests.
        
        Args:
            subnet (str): The subnet to scan in CIDR notation
            
        Returns:
            list: List of tuples containing (ip, mac) pairs
        """
        try:
            if not self.running:
                return []
                
            logger.info(f"Starting network scan on subnet {subnet}")
            
            # Create ARP request packet
            arp = ARP(pdst=subnet)
            ether = Ether(dst="ff:ff:ff:ff:ff:ff")
            packet = ether/arp

            # Send packet and get responses with shorter timeout
            logger.debug("Sending ARP packets...")
            result = srp(packet, timeout=2, verbose=0, inter=0.1)[0]  # Faster packet sending
            
            # Process responses
            devices = []
            for sent, received in result:
                devices.append((received.psrc, received.hwsrc))
                logger.debug(f"Discovered device: {received.psrc} ({received.hwsrc})")
            
            logger.info(f"Scan complete. Found {len(devices)} devices")
            return devices
            
        except Exception as e:
            logger.error(f"Error scanning network: {str(e)}", exc_info=True)
            return []
            
    def _update_database(self, devices):
        """
        Update the database with discovered devices.
        
        Args:
            devices (list): List of (ip, mac) tuples
        """
        if not self.running:
            return
            
        try:
            if not hasattr(self, '_db_conn') or self._db_conn.closed:
                self._db_conn = psycopg2.connect(**DB_CONFIG)
            conn = self._db_conn
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
                        profile['hostname'] if 'hostname' in profile else old_hostname,
                        profile['vendor'] if 'vendor' in profile else old_vendor,
                        profile['open_ports'] if 'open_ports' in profile else [],
                        device_id
                    ))
                    
                    # Log the discovery for activity tracking
                    cur.execute("""
                        INSERT INTO discovery_log (
                            mac_address,
                            ip_address,
                            timestamp,
                            is_known
                        ) VALUES (%s, %s, %s, TRUE)
                    """, (
                        mac,
                        ip,
                        now
                    ))
                    
                else:
                    # Insert new device into devices and new_devices tables
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
                        RETURNING id
                    """, (
                        mac,
                        ip,
                        now,
                        now,
                        profile['hostname'] if 'hostname' in profile else 'Unknown',
                        profile['vendor'] if 'vendor' in profile else 'Unknown',
                        profile['open_ports'] if 'open_ports' in profile else []
                    ))
                    
                    device_id = cur.fetchone()[0]
                    
                    # Add to new_devices for review
                    cur.execute("""
                        INSERT INTO new_devices (
                            device_name,
                            mac_address,
                            device_type,
                            last_seen,
                            last_ip,
                            notes,
                            first_seen,
                            reviewed
                        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    """, (
                        profile['hostname'] if 'hostname' in profile else 'Unknown',
                        mac,
                        'unknown',
                        now,
                        ip,
                        'Automatically detected by network scanner',
                        now,
                        False
                    ))
                    
                    # Send notifications for new device
                    device_info = f"New device detected:\nMAC: {mac}\nIP: {ip}\nHostname: {profile['hostname'] if 'hostname' in profile else 'Unknown'}\nVendor: {profile['vendor'] if 'vendor' in profile else 'Unknown'}"
                    
                    # Send notifications within Flask app context
                    with self.app.app_context():
                        try:
                            self.email_notifier.notify("New Device Detected", device_info)
                        except Exception as e:
                            logger.error(f"Failed to send email notification: {e}")
                        
                        try:
                            asyncio.run(self.telegram_notifier.notify_new_device_detected({
                                'mac': mac,
                                'ip': ip,
                                'hostname': profile['hostname'] if 'hostname' in profile else 'Unknown',
                                'vendor': profile['vendor'] if 'vendor' in profile else 'Unknown',
                                'first_seen': now.strftime('%Y-%m-%d %H:%M:%S')
                            }))
                        except Exception as e:
                            logger.error(f"Failed to send telegram notification: {e}")
                    
                    # Log the new device for the alert daemon to handle
                    logger.info(f"New device discovered: {device_info}")
            
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

if __name__ == "__main__":
    scanner = NetworkScanner()
    try:
        # Check for other instances
        if not scanner.acquire_lock():
            logger.error("Another instance is already running. Exiting.")
            sys.exit(1)
            
        # Banner
        print("🛡️ Netureon", __version__)
        print("✨ Network monitoring and security management system")
        
        # Initialize and start scanner
        scanner.start_monitoring()
    except KeyboardInterrupt:
        print("\nShutting down...")
    except Exception as e:
        logger.error(f"Fatal error: {str(e)}")
        raise
    finally:
        # Clean up
        scanner.release_lock()
        logger.info("Scanner shutdown complete")
