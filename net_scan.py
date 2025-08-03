import psycopg2
import netifaces
from scapy.all import ARP, Ether, srp
from datetime import datetime
import ipaddress
import os
from dotenv import load_dotenv
from device_profiler import DeviceProfiler

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
    try:
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
    arp = ARP(pdst=subnet)
    ether = Ether(dst="ff:ff:ff:ff:ff:ff")
    packet = ether / arp
    result = srp(packet, timeout=3, verbose=0)[0]

    devices = []
    for sent, received in result:
        devices.append((received.psrc, received.hwsrc))
    return devices

def update_database(devices):
    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor()

    for ip, mac in devices:
        timestamp = datetime.now()

        # Check device status across all tables
        cur.execute("""
            SELECT 
                CASE 
                    WHEN EXISTS (SELECT 1 FROM known_devices WHERE mac_address = %s::macaddr) THEN 'known'
                    WHEN EXISTS (SELECT 1 FROM unknown_devices WHERE mac_address = %s::macaddr) THEN 'threat'
                    WHEN EXISTS (SELECT 1 FROM new_devices WHERE mac_address = %s::macaddr) THEN 'new'
                    ELSE 'unregistered'
                END as device_status
        """, (mac, mac, mac))
        status = cur.fetchone()[0]

        # Log discovery
        cur.execute("""
            INSERT INTO discovery_log (mac_address, ip_address, timestamp, is_known)
            VALUES (%s::macaddr, %s::inet, %s, %s)
        """, (mac, ip, timestamp, status == 'known'))

        # Handle device based on its status
        if status == 'known':
            # Update known device's last seen time
            cur.execute("""
                UPDATE known_devices 
                SET last_seen = %s, last_ip = %s::inet 
                WHERE mac_address = %s::macaddr
            """, (timestamp, ip, mac))
        elif status == 'threat':
            # Update threat device's last seen time
            cur.execute("""
                UPDATE unknown_devices 
                SET last_seen = %s, last_ip = %s 
                WHERE mac_address::text = %s
            """, (timestamp, ip, mac))
        elif status == 'new':
            # Update new device's last seen time
            cur.execute("""
                UPDATE new_devices 
                SET last_seen = %s, last_ip = %s::inet
                WHERE mac_address = %s::macaddr
            """, (timestamp, ip, mac))
        else:  # unregistered
            # Profile device
            profiler = DeviceProfiler(mac, ip)
            vendor = profiler.get_mac_vendor()
            hostname = profiler.get_hostname()
            open_ports = profiler.scan_open_ports()

            notes = f"Vendor: {vendor}, Hostname: {hostname}"
            if open_ports:
                notes += f", Open Ports: {', '.join(map(str, open_ports))}"
            else:
                notes += ", No common ports open"

            # Insert new device for review
            cur.execute("""
                INSERT INTO new_devices (
                    mac_address, first_seen, last_seen, last_ip, 
                    reviewed, device_name, device_type, notes
                ) VALUES (%s::macaddr, %s, %s, %s::inet, FALSE, %s, %s, %s)
            """, (mac, timestamp, timestamp, ip, hostname, vendor, notes))

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
