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
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

DB_CONFIG = {
    'dbname': os.getenv('DB_NAME'),
    'user': os.getenv('DB_USER'),
    'password': os.getenv('DB_PASSWORD'),
    'host': os.getenv('DB_HOST'),
    'port': os.getenv('DB_PORT')
}

class NetworkScanner:
    def __init__(self, single_scan=False):
        self.setup_logging()
        self.notifier = sdnotify.SystemdNotifier()
        self.running = True
        self.last_watchdog = time.time()
        self.watchdog_interval = 30
        self.single_scan = single_scan
        self.db_conn = None
        self.logger.info("Netureon Scanner v1.3.1 initialized")

    def setup_logging(self):
        log_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'logs')
        os.makedirs(log_dir, exist_ok=True)
        
        log_file = os.path.join(log_dir, 'netureon.log')
        
        handler = RotatingFileHandler(
            log_file,
            maxBytes=10*1024*1024,
            backupCount=5,
            delay=False,
            mode='a'
        )
        
        formatter = logging.Formatter(
            '%(asctime)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        handler.setFormatter(formatter)
        
        self.logger = logging.getLogger()
        self.logger.setLevel(logging.INFO)
        
        for h in self.logger.handlers[:]:
            self.logger.removeHandler(h)
            
        self.logger.addHandler(handler)
        handler.flush()
        return self.logger

    def connect_db(self):
        try:
            if not self.db_conn or self.db_conn.closed:
                self.db_conn = psycopg2.connect(**DB_CONFIG)
                self.db_conn.autocommit = True
        except Exception as e:
            self.logger.error(f"Database connection failed: {e}")
            raise

    def scan_network(self):
        try:
            self.logger.info("Starting network scan...")
            self.connect_db()
            self.ping_watchdog()
            
            devices = []
            for subnet in ["192.168.1.0/24"]:  # Add more subnets if needed
                arp = ARP(pdst=subnet)
                ether = Ether(dst="ff:ff:ff:ff:ff:ff")
                packet = ether/arp

                result = srp(packet, timeout=3, verbose=0)[0]
                chunk_devices = [(received.psrc, received.hwsrc) for sent, received in result]
                devices.extend(chunk_devices)
                self.ping_watchdog()

            self.process_devices(devices)
            self.logger.info(f"Scan complete. Found {len(devices)} devices")
            return True
            
        except Exception as e:
            self.logger.error(f"Scan failed: {str(e)}")
            return False
        finally:
            if self.db_conn:
                self.db_conn.close()

    def process_devices(self, devices):
        cur = self.db_conn.cursor()
        try:
            for ip, mac in devices:
                cur.execute("""
                    INSERT INTO new_devices (mac_address, last_ip, last_seen)
                    VALUES (%s::macaddr, %s::inet, NOW())
                    ON CONFLICT (mac_address) DO UPDATE 
                    SET last_ip = EXCLUDED.last_ip,
                        last_seen = NOW()
                """, (mac, ip))
        finally:
            cur.close()

    def ping_watchdog(self):
        current_time = time.time()
        if current_time - self.last_watchdog >= self.watchdog_interval:
            self.notifier.notify("WATCHDOG=1")
            self.last_watchdog = current_time

    def handle_shutdown(self, signum, frame):
        self.logger.info("Received shutdown signal, cleaning up...")
        self.running = False
        if self.db_conn:
            self.db_conn.close()
        self.logger.info("Scanner shutdown complete")
        sys.exit(0)

    def start_monitoring(self):
        try:
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
