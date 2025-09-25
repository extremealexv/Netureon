"""Network scanning module for Netureon.

This module provides network discovery and device tracking functionality using
ARP scanning and device profiling capabilities.
"""

import os
import sys
import time
import logging
from logging.handlers import RotatingFileHandler
import sdnotify
from scapy.all import ARP, Ether, srp
import psycopg2
from concurrent.futures import ThreadPoolExecutor
import argparse
import signal
from dotenv import load_dotenv
from netureon.config.logging_config import configure_logger, get_logging_level_from_db

# Load environment variables
load_dotenv()

class NetworkScanner:
    def __init__(self, single_scan=False):
        self.setup_logging()
        self.setup_signal_handlers()
        self.notifier = sdnotify.SystemdNotifier()
        self.running = True
        self.last_watchdog = time.time()
        self.watchdog_interval = 30
        self.single_scan = single_scan
        self.db_config = {
            'dbname': os.getenv('DB_NAME'),
            'user': os.getenv('DB_USER'),
            'password': os.getenv('DB_PASSWORD'),
            'host': os.getenv('DB_HOST'),
            'port': os.getenv('DB_PORT')
        }
        self.db_conn = None
        self.logger.info("Netureon Scanner v1.3.1 initialized")

    def setup_logging(self):
        """Configure logging with proper file handling using database configuration"""
        log_dir = os.path.expanduser('~/Netureon/logs')
        log_file = os.path.join(log_dir, 'netureon.log')
        
        # Use centralized logging configuration that reads from database
        self.logger = configure_logger('netureon', log_file)
        
        # Log the current configuration
        db_level = get_logging_level_from_db()
        self.logger.info(f"Scanner logging configured to level: {logging.getLevelName(db_level)}")
        
        return self.logger

    def setup_signal_handlers(self):
        """Set up signal handlers for graceful shutdown."""
        # Handle SIGTERM for graceful shutdown
        signal.signal(signal.SIGTERM, self.signal_handler)
        # Handle SIGINT (Ctrl+C) for graceful shutdown
        signal.signal(signal.SIGINT, self.signal_handler)
        
        self.logger.debug("Signal handlers configured")

    def signal_handler(self, signum, frame):
        """Handle shutdown signals."""
        self.logger.info(f"Received signal {signum}, shutting down gracefully...")
        self.running = False

    def connect_db(self):
        """Establish database connection"""
        try:
            if not self.db_conn or self.db_conn.closed:
                self.db_conn = psycopg2.connect(**self.db_config)
                self.db_conn.autocommit = False
                self.logger.debug("Database connection established")
        except Exception as e:
            self.logger.error(f"Database connection failed: {e}")
            raise

    def scan_network(self):
        """Perform network scan"""
        try:
            self.logger.info("Starting network scan...")
            self.connect_db()  # Ensure DB connection is established
            self.ping_watchdog()
            
            devices = []
            arp = ARP(pdst="192.168.1.0/24")
            ether = Ether(dst="ff:ff:ff:ff:ff:ff")
            packet = ether/arp

            result = srp(packet, timeout=3, verbose=0)[0]
            devices = [(received.psrc, received.hwsrc) for sent, received in result]
            
            self.process_devices(devices)
            self.logger.info(f"Scan complete. Found {len(devices)} devices")
            return True
            
        except Exception as e:
            self.logger.error(f"Scan failed: {str(e)}")
            return False
        finally:
            if self.db_conn:
                self.db_conn.close()
                self.db_conn = None

    def process_devices(self, devices):
        """Process discovered devices and only add new ones to review"""
        if not self.db_conn:
            self.connect_db()
            
        cur = self.db_conn.cursor()
        try:
            for ip, mac in devices:
                # First check if device is already known
                cur.execute("""
                    SELECT EXISTS (
                        SELECT 1 FROM known_devices 
                        WHERE mac_address = %s::macaddr
                    )
                """, (mac,))
                is_known = cur.fetchone()[0]

                if not is_known:
                    # Then check if it's already in review
                    cur.execute("""
                        SELECT EXISTS (
                            SELECT 1 FROM new_devices 
                            WHERE mac_address = %s::macaddr
                        )
                    """, (mac,))
                    in_review = cur.fetchone()[0]

                    # Also check if it's already in unknown_devices (blocked)
                    cur.execute("""
                        SELECT EXISTS (
                            SELECT 1 FROM unknown_devices 
                            WHERE mac_address = %s::macaddr
                        )
                    """, (mac,))
                    is_blocked = cur.fetchone()[0]

                    if not in_review and not is_blocked:
                        # Only add to new_devices if truly new and not blocked
                        cur.execute("""
                            INSERT INTO new_devices (mac_address, last_ip, last_seen)
                            VALUES (%s::macaddr, %s::inet, NOW())
                        """, (mac, ip))
                        self.logger.info(f"New device detected: MAC={mac}, IP={ip}")
                    elif in_review:
                        # Just update last seen for existing review devices
                        cur.execute("""
                            UPDATE new_devices 
                            SET last_ip = %s::inet,
                                last_seen = NOW()
                            WHERE mac_address = %s::macaddr
                        """, (ip, mac))
                    elif is_blocked:
                        # Update blocked device activity in unknown_devices
                        cur.execute("""
                            UPDATE unknown_devices 
                            SET last_ip = %s::inet,
                                last_seen = NOW()
                            WHERE mac_address = %s::macaddr
                        """, (ip, mac))
                        self.logger.debug(f"Updated blocked device activity: MAC={mac}, IP={ip}")

                # Update known devices activity
                cur.execute("""
                    UPDATE known_devices 
                    SET last_ip = %s::inet,
                        last_seen = NOW(),
                        status = 'active'
                    WHERE mac_address = %s::macaddr
                """, (ip, mac))

            # Mark devices not seen in this scan as inactive
            cur.execute("""
                UPDATE known_devices
                SET status = 'inactive'
                WHERE last_seen < NOW() - INTERVAL '5 minutes'
            """)
            
            self.db_conn.commit()
        except Exception as e:
            self.logger.error(f"Error processing devices: {str(e)}")
            self.db_conn.rollback()
            raise
        finally:
            cur.close()

    def ping_watchdog(self):
        """Send watchdog notification to systemd"""
        try:
            current_time = time.time()
            if current_time - self.last_watchdog >= self.watchdog_interval:
                self.notifier.notify("WATCHDOG=1")
                self.last_watchdog = current_time
                self.logger.debug("Watchdog notification sent")
        except Exception as e:
            self.logger.error(f"Watchdog notification failed: {str(e)}")

    def handle_shutdown(self, signum, frame):
        """Handle shutdown signals gracefully"""
        self.logger.info(f"Received signal {signum}, cleaning up...")
        self.running = False
        self.logger.info("Scanner shutdown complete")
        sys.exit(0)

    def start_monitoring(self):
        """Start the monitoring process"""
        try:
            self.logger.info("Starting network monitoring...")
            self.notifier.notify("READY=1")
            
            if self.single_scan:
                self.scan_network()
                return
                
            while self.running:
                self.scan_network()
                self.ping_watchdog()
                
                # Sleep in smaller intervals to respond to shutdown faster
                for _ in range(30):  # 5 minutes = 30 * 10 seconds
                    if not self.running:
                        break
                    time.sleep(10)
                    self.ping_watchdog()
                
        except Exception as e:
            self.logger.error(f"Error in monitoring: {str(e)}")
            sys.exit(1)

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--scan-once', action='store_true', help='Perform single scan and exit')
    args = parser.parse_args()
    
    scanner = NetworkScanner(single_scan=args.scan_once)
    scanner.start_monitoring()
