import psycopg2
from device_profiler import DeviceProfiler
from datetime import datetime
import os
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

def format_notes(vendor, hostname, open_ports):
    return (
        f"Vendor: {vendor}\n"
        f"Hostname: {hostname}\n"
        f"Open Ports: {', '.join(map(str, open_ports)) if open_ports else 'None'}"
    )

def promote_devices():
    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor()

    # Fetch unreviewed new devices
    cur.execute("""
        SELECT mac_address::macaddr::text, last_ip FROM new_devices
        WHERE reviewed = FALSE AND last_ip IS NOT NULL
    """)
    devices = cur.fetchall()

    print(f"🔎 Profiling {len(devices)} new device(s)...")

    for mac, ip in devices:
        profiler = DeviceProfiler(mac, str(ip))
        vendor = profiler.get_mac_vendor()
        hostname = profiler.get_hostname()
        ports = profiler.scan_open_ports()
        notes = format_notes(vendor, hostname, ports)
        timestamp = datetime.now()

        # Insert into known_devices
        cur.execute("""
            INSERT INTO known_devices (mac_address, device_name, device_type, notes, first_seen, last_seen, last_ip)
            VALUES (%s::macaddr, %s, %s, %s, %s, %s, %s::inet)
            ON CONFLICT (mac_address) DO NOTHING
        """, (mac, hostname, vendor, notes, timestamp, timestamp, ip))

        # Mark device as reviewed
        cur.execute("""
            UPDATE new_devices SET reviewed = TRUE WHERE mac_address = %s
        """, (mac,))

        print(f"✅ {mac} promoted to known_devices.")

    conn.commit()
    cur.close()
    conn.close()
    print("📦 Promotion complete.")

if __name__ == "__main__":
    promote_devices()
