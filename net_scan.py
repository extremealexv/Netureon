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
from webui.config.config import Config
import socket
import psutil
import subprocess
import sdnotify
import signal
import fcntl
import sys
import os.path

# Configure logging
log_dir = os.path.expanduser('~/Netureon/logs')
os.makedirs(log_dir, exist_ok=True)
log_file = os.path.join(log_dir, 'netureon.log')

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(log_file)
    ]
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
    Detect and return the local subnet for scanning.
    Returns:
        str: CIDR notation of the local subnet (e.g., '192.168.1.0/24')
    """
    for iface in netifaces.interfaces():
        if iface == 'lo' or not netifaces.AF_INET in netifaces.ifaddresses(iface):
            continue
        
        ipv4_info = netifaces.ifaddresses(iface)[netifaces.AF_INET][0]
        ip = ipv4_info['addr']
        netmask = ipv4_info['netmask']
        
        if ip and netmask:
            ip_interface = ipaddress.IPv4Interface(f"{ip}/{netmask}")
            network = ip_interface.network
            if network.is_private:
                return str(network)

    raise RuntimeError("No active LAN interface with IPv4 found.")

class NetworkScanner:
    def __init__(self):
        """Initialize the network scanner."""
        self.running = False
        self.app = create_app()
        self.email_notifier = EmailNotifier()
        self.telegram_notifier = TelegramNotifier()
        self.lock_file = '/tmp/netureon_scanner.lock'
        self.notifier = sdnotify.SystemdNotifier()
        self.last_watchdog = 0
        self.watchdog_interval = 30  # 30 seconds watchdog interval
        
        # Setup signal handlers
        signal.signal(signal.SIGTERM, self.handle_shutdown)
        signal.signal(signal.SIGINT, self.handle_shutdown)
        
        # Test database connection early
        try:
            with psycopg2.connect(**DB_CONFIG):
                pass
            logger.info("Database connection test successful")
        except Exception as e:
            logger.error(f"Database connection failed: {e}")
            sys.exit(1)
        
        # Notify systemd we're starting up
        logger.info("Sending READY=1 to systemd...")
        if not self.notifier.notify("READY=1"):
            logger.error("Failed to notify systemd of readiness")
            sys.exit(1)
        logger.info("Successfully notified systemd of readiness")
    
    def ping_watchdog(self):
        """Send watchdog keep-alive signal to systemd."""
        current_time = time.time()
        if current_time - self.last_watchdog >= self.watchdog_interval:
            if not self.notifier.notify("WATCHDOG=1"):
                logger.error("Failed to send watchdog notification")
                self.handle_shutdown(signal.SIGTERM, None)
            self.last_watchdog = current_time
            logger.debug("Watchdog notification sent")
    
    def acquire_lock(self):
        """Try to acquire the lock file to prevent multiple instances."""
        try:
            self.lock_fd = open(self.lock_file, 'w')
            fcntl.lockf(self.lock_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            self.lock_fd.write(str(os.getpid()))
            self.lock_fd.flush()
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
        
        if hasattr(self, '_db_conn') and self._db_conn:
            try:
                self._db_conn.close()
            except:
                pass
        
        self.release_lock()
        logger.info("Scanner shutdown complete")
        self.notifier.notify("STOPPING=1")
        sys.exit(0)
    
    def cleanup_existing_process(self):
        """Find and cleanup any existing Netureon processes."""
        try:
            # Check lock file
            if os.path.exists(self.lock_file):
                try:
                    with open(self.lock_file, 'r') as f:
                        old_pid = int(f.read().strip())
                        if psutil.pid_exists(old_pid):
                            logger.info(f"Found existing Netureon process (PID: {old_pid})")
                            try:
                                old_process = psutil.Process(old_pid)
                                old_process.terminate()
                                old_process.wait(timeout=10)
                            except (psutil.NoSuchProcess, psutil.TimeoutExpired):
                                subprocess.run(['sudo', 'kill', '-9', str(old_pid)], 
                                            check=False)
                except Exception as e:
                    logger.warning(f"Error reading lock file: {e}")

            # Look for other instances
            for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
                try:
                    cmdline = proc.info['cmdline']
                    if cmdline and 'net_scan.py' in ' '.join(cmdline) and proc.pid != os.getpid():
                        logger.info(f"Found another Netureon process (PID: {proc.pid})")
                        proc.terminate()
                        try:
                            proc.wait(timeout=10)
                        except psutil.TimeoutExpired:
                            proc.kill()
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue

            # Clean up lock file
            if os.path.exists(self.lock_file):
                os.unlink(self.lock_file)
            
            time.sleep(2)
            return True
            
        except Exception as e:
            logger.error(f"Error during process cleanup: {e}")
            return False
    
    def start_monitoring(self):
        """Start the network monitoring loop."""
        if not self.cleanup_existing_process():
            logger.error("Failed to cleanup existing processes")
            self.notifier.notify("STATUS=Failed to cleanup")
            sys.exit(1)
            
        if not self.acquire_lock():
            logger.error("Failed to acquire lock. Another instance may be running.")
            self.notifier.notify("STATUS=Failed to start - lock exists")
            sys.exit(1)
            
        self.running = True
        self.notifier.notify("STATUS=Starting network monitoring...")
        logger.info("Starting network monitoring...")
        
        try:
            from threading import Thread
            webapp_thread = Thread(target=self.app.run, 
                                kwargs={
                                    'host': Config.WEB_HOST,
                                    'port': Config.WEB_PORT,
                                    'debug': Config.WEB_DEBUG,
                                    'use_reloader': False
                                })
            webapp_thread.daemon = True
            webapp_thread.start()
            logger.info(f"Web interface started on {Config.WEB_HOST}:{Config.WEB_PORT}")
            
            # Notify systemd we're fully running
            self.notifier.notify("STATUS=Running")
            
            while self.running:
                try:
                    interval = int(os.getenv('SCAN_INTERVAL', 300))
                    chunks = interval // self.watchdog_interval
                    remainder = interval % self.watchdog_interval
                    
                    for _ in range(chunks):
                        if not self.running:
                            break
                        time.sleep(self.watchdog_interval)
                        self.ping_watchdog()
                    
                    if remainder and self.running:
                        time.sleep(remainder)
                        self.ping_watchdog()
                    
                    if not self.running:
                        break
                        
                    subnet = get_local_subnet()
                    devices = self.scan_network(subnet)
                    self._update_database(devices)
                    self.ping_watchdog()
                except Exception as e:
                    logger.error(f"Error in main loop: {e}")
                    if self.running:
                        time.sleep(self.watchdog_interval)
                        self.ping_watchdog()
                        
        finally:
            self.release_lock()
    
    def scan_network(self, subnet):
        """Scan the network using multiple methods."""
        self.ping_watchdog()
        try:
            if not self.running:
                return []
                
            logger.info(f"Starting network scan on subnet {subnet}")
            devices = set()
            
            network = ipaddress.ip_network(subnet)
            chunk_size = 32
            total_chunks = (network.num_addresses + chunk_size - 1) // chunk_size
            
            for attempt in range(2):
                for chunk_idx in range(total_chunks):
                    if not self.running:
                        return list(devices)
                        
                    start_ip = network[chunk_idx * chunk_size]
                    end_ip = network[min((chunk_idx + 1) * chunk_size - 1, network.num_addresses - 1)]
                    chunk_subnet = f"{start_ip}/{network.prefixlen}"
                    
                    arp = ARP(pdst=chunk_subnet)
                    ether = Ether(dst="ff:ff:ff:ff:ff:ff")
                    packet = ether/arp
                    
                    logger.debug(f"Scanning chunk {chunk_idx + 1}/{total_chunks} (attempt {attempt + 1})")
                    result = srp(packet, timeout=1, verbose=0, inter=0.01, retry=1, multi=True)[0]
                    
                    for sent, received in result:
                        devices.add((received.psrc, received.hwsrc))
                    
                    self.ping_watchdog()
                
                if attempt < 1:
                    time.sleep(0.5)
                    self.ping_watchdog()
            
            try:
                with os.popen('arp -n') as f:
                    for line in f:
                        if '(' in line or 'Address' in line:
                            continue
                        parts = line.strip().split()
                        if len(parts) >= 3:
                            ip, mac = parts[0], parts[2]
                            if ip and mac and mac != '00:00:00:00:00:00':
                                devices.add((ip, mac))
            except Exception as e:
                logger.warning(f"Failed to read system ARP cache: {e}")
            
            device_list = list(devices)
            logger.info(f"Scan complete. Found {len(device_list)} devices")
            self.ping_watchdog()
            return device_list
            
        except Exception as e:
            logger.error(f"Error scanning network: {str(e)}", exc_info=True)
            return []
    
    def _update_database(self, devices):
        """Update the database with discovered devices."""
        if not self.running:
            return
            
        try:
            if not hasattr(self, '_db_conn') or self._db_conn.closed:
                self._db_conn = psycopg2.connect(**DB_CONFIG)
            conn = self._db_conn
            cur = conn.cursor()
            
            # Get current active devices
            cur.execute("SELECT mac_address, status FROM known_devices WHERE status = 'active'")
            active_devices = {row[0]: row[1] for row in cur.fetchall()}
            
            now = datetime.now()
            
            chunk_size = 5
            for i in range(0, len(devices), chunk_size):
                if not self.running:
                    return
                    
                chunk = devices[i:i + chunk_size]
                for ip, mac in chunk:
                    if ip in ['127.0.0.1', '255.255.255.255'] or mac == 'ff:ff:ff:ff:ff:ff':
                        continue
                        
                    profiler = DeviceProfiler(mac, ip)
                    profile = profiler.profile()
                    
                    cur.execute("""
                        SELECT mac_address FROM known_devices 
                        WHERE mac_address = %s
                    """, (mac,))
                    device_exists = cur.fetchone()
                    
                    if device_exists:
                        cur.execute("""
                            UPDATE known_devices 
                            SET last_ip = %s,
                                last_seen = %s,
                                status = 'active',
                                open_ports = %s,
                                hostname = %s,
                                vendor = %s
                            WHERE mac_address = %s
                        """, (ip, now, profile.get('open_ports', []), 
                             profile.get('hostname', 'Unknown'),
                             profile.get('vendor', 'Unknown'), mac))
                    else:
                        cur.execute("""
                            INSERT INTO new_devices 
                            (mac_address, last_ip, first_seen, last_seen, 
                             hostname, vendor, open_ports, reviewed)
                            VALUES (%s, %s, %s, %s, %s, %s, %s, false)
                            ON CONFLICT (mac_address) DO UPDATE 
                            SET last_ip = EXCLUDED.last_ip,
                                last_seen = EXCLUDED.last_seen,
                                hostname = EXCLUDED.hostname,
                                vendor = EXCLUDED.vendor,
                                open_ports = EXCLUDED.open_ports
                        """, (mac, ip, now, now, 
                             profile.get('hostname', 'Unknown'),
                             profile.get('vendor', 'Unknown'),
                             profile.get('open_ports', [])))
                    
                    if mac in active_devices:
                        del active_devices[mac]
                    
                    self.ping_watchdog()
                    
            for mac in active_devices:
                cur.execute("""
                    UPDATE known_devices 
                    SET status = 'inactive'
                    WHERE mac_address = %s
                """, (mac,))
                
            conn.commit()
            
        except Exception as e:
            logger.error(f"Database error: {str(e)}")
            if 'conn' in locals():
                conn.rollback()
            raise
        finally:
            if 'cur' in locals():
                cur.close()

if __name__ == "__main__":
    scanner = NetworkScanner()
    try:
        scanner.start_monitoring()
    except KeyboardInterrupt:
        scanner.handle_shutdown(signal.SIGINT, None)
    except Exception as e:
        logger.error(f"Fatal error: {str(e)}")
        scanner.handle_shutdown(signal.SIGTERM, None)
        raise
