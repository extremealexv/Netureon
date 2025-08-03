import psycopg2
import smtplib
import requests
import time
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Database config
DB_CONFIG = {
    'dbname': os.getenv('DB_NAME'),
    'user': os.getenv('DB_USER'),
    'password': os.getenv('DB_PASSWORD'),
    'host': os.getenv('DB_HOST'),
    'port': os.getenv('DB_PORT')
}

# Email config
EMAIL_FROM = os.getenv('EMAIL_FROM')
EMAIL_TO = os.getenv('EMAIL_TO')
EMAIL_SUBJECT = os.getenv('EMAIL_SUBJECT', 'Intrusion Alert')
SMTP_SERVER = os.getenv('SMTP_SERVER')
SMTP_PORT = int(os.getenv('SMTP_PORT', '587'))
SMTP_USER = os.getenv('SMTP_USER')
SMTP_PASSWORD = os.getenv('SMTP_PASSWORD')

# Telegram config
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

def send_email(body):
    try:
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls()
            server.login(SMTP_USER, SMTP_PASSWORD)
            message = f"Subject:{EMAIL_SUBJECT}\n\n{body}"
            server.sendmail(EMAIL_FROM, EMAIL_TO, message)
    except Exception as e:
        print(f"Email error: {e}")

# def send_telegram(message):
#     url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
#     payload = {"chat_id": TELEGRAM_CHAT_ID, "text": message}
#     try:
#         requests.post(url, data=payload)
#     except Exception as e:
#         print(f"Telegram error: {e}")

def format_device_info(mac, ip, hostname, vendor, ports):
    """Format device information for alerts."""
    return f"""
🔍 Device Details:
MAC: {mac}
IP: {ip}
Hostname: {hostname or 'Unknown'}
Vendor: {vendor or 'Unknown'}
Open Ports: {', '.join(map(str, ports)) if ports else 'None detected'}
    """.strip()

def check_for_unknown_devices():
    """Check discovery_log for any connections from unknown devices."""
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cursor = conn.cursor()
        
        # Get recent connections that match unknown devices with detailed info
        cursor.execute("""
            SELECT 
                dl.mac_address, 
                dl.ip_address, 
                dl.timestamp, 
                ud.threat_level, 
                ud.notes,
                ud.first_seen,
                (
                    SELECT COUNT(*) 
                    FROM discovery_log 
                    WHERE mac_address = dl.mac_address
                ) as detection_count,
                dp.hostname,
                dp.vendor,
                dp.open_ports
            FROM discovery_log dl
            JOIN unknown_devices ud ON dl.mac_address = ud.mac_address
            LEFT JOIN device_profiles dp ON dl.mac_address = dp.mac_address
            WHERE dl.timestamp > NOW() - INTERVAL '5 minutes'
        """)
        unknown_connections = cursor.fetchall()

        # Create alerts for unknown device connections
        for mac, ip, timestamp, threat_level, notes, first_seen, count, hostname, vendor, ports in unknown_connections:
            # Update last_seen in unknown_devices
            cursor.execute("""
                UPDATE unknown_devices 
                SET last_seen = %s, last_ip = %s 
                WHERE mac_address = %s
            """, (timestamp, ip, mac))

            # Format complete alert details
            device_info = format_device_info(mac, ip, hostname, vendor, ports or [])
            alert_details = f"""
⚠️ THREAT DETECTED: {threat_level.upper()} Risk Device
{device_info}

📊 History:
First Seen: {first_seen}
Total Detections: {count}

🚫 Threat Notes: 
{notes}
            """.strip()

            # Create a single alert
            cursor.execute("""
                INSERT INTO alerts (device_id, detected_at, alert_type, details, severity)
                VALUES (%s, %s, 'unknown_device', %s, %s)
                ON CONFLICT (device_id, alert_type) WHERE NOT is_resolved
                DO UPDATE SET detected_at = EXCLUDED.detected_at, 
                            details = EXCLUDED.details,
                            severity = EXCLUDED.severity
            """, (mac, timestamp, alert_details, threat_level))

        conn.commit()
        cursor.close()
        conn.close()
    except Exception as e:
        print(f"Error checking unknown devices: {e}")

def check_alerts():
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, device_id, detected_at, alert_type, details, severity 
            FROM alerts 
            WHERE NOT is_resolved 
            ORDER BY severity DESC, detected_at ASC
        """)
        rows = cursor.fetchall()

        for alert_id, device_id, timestamp, alert_type, details, severity in rows:
            # Format message based on alert type
            if alert_type == 'new_device':
                body = f"🆕 New Device Detected\nMAC: {device_id}\nTime: {timestamp}\nDetails: {details}"
            elif alert_type == 'unknown_device':
                body = f"⚠️ ALERT: {severity.upper()} Risk Threat Device Connected\n{details}\nDetected at: {timestamp}"
            else:
                body = f"Alert ({severity}): {details}\nDevice: {device_id}\nTime: {timestamp}"

            send_email(body)
            # send_telegram(body)
            cursor.execute("UPDATE alerts SET is_resolved = TRUE WHERE id = %s", (alert_id,))

        conn.commit()
        cursor.close()
        conn.close()

    except Exception as e:
        print(f"Database error: {e}")

if __name__ == "__main__":
    print("🔔 Alert daemon started...")
    while True:
        check_for_unknown_devices()  # Check for unknown device connections
        check_alerts()               # Process pending alerts
        time.sleep(10)  # Check every 10 seconds
