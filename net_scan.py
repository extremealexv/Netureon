import psycopg2
import netifaces
from scapy.all import ARP, Ether, srp
from datetime import datetime
import ipaddress
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# PostgreSQL connection settings
DB_CONFIG = {
    'dbname': os.getenv('DB_NAME'),
    'user': os.getenv('DB_USER'),
    'password': os.getenv('DB_PASSWORD'),
    'host': os.getenv('DB_HOST'),
    'port': os.getenv('DB_PORT')
}

def get_local_subnet():
    """Detects the local subnet using the default route interface."""
    try:
        # Get default gateway interface
        gws = netifaces.gateways()
        default_iface = gws['default'][netifaces.AF_INET][1]

        addrs = netifaces.ifaddresses(default_iface)
        if netifaces.AF_INET in addrs:
            inet_info = addrs[netifaces.AF_INET][0]
            ip = inet_info.get('addr')
            netmask = inet_info.get('netmask')
            if ip and netmask and not ip.startswith("127."):
                network = ipaddress.IPv4Network(f"{ip}/{netmask}", strict=False)
                return str(network)
    except Exception as e:
        print(f"⚠️ Failed to detect default interface: {e}")

    # Fallback: scan all interfaces
    for iface in netifaces.interfaces():
        if "Virtual" in iface or "VMware" in iface or "Loopback" in iface:
            continue

        addrs = netifaces.ifaddresses(iface)
        if netifaces.AF_INET in addrs:
            inet_info = addrs[netifaces.AF_INET][0]
            ip = inet_info.get('addr')
            netmask = inet_info.get('netmask')
            if ip and netmask and not ip.startswith("127."):
                network = ipaddress.IPv4Network(f"{ip}/{netmask}", strict=False)
                return str(network)

    raise RuntimeError("No active LAN interface with IPv4 found.")

def scan_network(subnet):
    """Scans the network and returns list of (IP, MAC) tuples."""
    arp = ARP(pdst=subnet)
    ether = Ether(dst="ff:ff:ff:ff:ff:ff")
    packet = ether / arp
    result = srp(packet, timeout=3, verbose=0)[0]

    devices = []
    for sent, received in result:
        devices.append((received.psrc, received.hwsrc))
    return devices

def update_database(devices):
    """Updates discovery_log and new_devices based on scan results."""
    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor()

    for ip, mac in devices:
        timestamp = datetime.now()

        # Check if device is known
        cur.execute("SELECT id FROM known_devices WHERE mac_address = %s", (mac,))
        known = cur.fetchone()

        # Log discovery
        cur.execute("""
            INSERT INTO discovery_log (mac_address, ip_address, timestamp, is_known)
            VALUES (%s, %s, %s, %s)
        """, (mac, ip, timestamp, bool(known)))

        if not known:
            # Check if already in new_devices
            cur.execute("SELECT id FROM new_devices WHERE mac_address = %s", (mac,))
            exists = cur.fetchone()

            if exists:
                # Update last_seen and last_ip
                cur.execute("""
                    UPDATE new_devices
                    SET last_seen = %s, last_ip = %s
                    WHERE mac_address = %s
                """, (timestamp, ip, mac))
            else:
                # Insert new unknown device
                cur.execute("""
                    INSERT INTO new_devices (mac_address, first_seen, last_seen, last_ip, reviewed)
                    VALUES (%s, %s, %s, %s, FALSE)
                """, (mac, timestamp, timestamp, ip))

    conn.commit()
    cur.close()
    conn.close()

if __name__ == "__main__":
    try:
        subnet = get_local_subnet()
        print(f"🔍 Scanning network: {subnet}")
        devices = scan_network(subnet)
        print(f"✅ Found {len(devices)} devices.")
        update_database(devices)
        print("📦 Database updated.")
    except Exception as e:
        print(f"❌ Error: {e}")
