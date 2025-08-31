import psycopg2
import smtplib
import requests
import time
import os
from datetime import datetime, timedelta

def main():
    # Connect to the PostgreSQL database
    conn = psycopg2.connect(
        dbname="netguard",
        user="netguard",
        password="netguard",
        host="localhost"
    )
    cur = conn.cursor()
    
    cur.execute("""
            WITH formatted_macs AS (
                SELECT 
                    dl.mac_address,
                    dl.ip_address,
                    dl.timestamp,
                    dl.mac_address::macaddr as formatted_mac
                FROM discovery_log dl
                WHERE dl.timestamp > NOW() - INTERVAL '5 minutes'
            )
            SELECT 
                fm.mac_address, 
                fm.ip_address, 
                fm.timestamp, 
                ud.threat_level, 
                ud.notes,
                ud.first_seen,
                (
                    SELECT COUNT(*) 
                    FROM discovery_log 
                    WHERE mac_address::macaddr = fm.formatted_mac
                ) as detection_count,
                dp.hostname,
                dp.vendor,
                dp.open_ports
            FROM formatted_macs fm
            JOIN unknown_devices ud ON fm.formatted_mac = ud.mac_address
            LEFT JOIN device_profiles dp ON fm.formatted_mac = dp.mac_address
            """)

# Load environment variables
from dotenv import load_dotenv
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
    missing = []
    for var, name in [
        (SMTP_SERVER, 'SMTP_SERVER'),
        (SMTP_PORT, 'SMTP_PORT'),
        (SMTP_USER, 'SMTP_USER'),
        (SMTP_PASSWORD, 'SMTP_PASSWORD'),
        (EMAIL_FROM, 'EMAIL_FROM'),
        (EMAIL_TO, 'EMAIL_TO')
    ]:
        if not var:
            missing.append(name)
    
    if missing:
        print(f"Email configuration incomplete. Missing: {', '.join(missing)}")
        print("Run setup_email.sh to configure email settings")
        return False
        
    try:
        print(f"Attempting to send email notification to {EMAIL_TO}")
        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
        server.set_debuglevel(1)  # Enable debug output
        
        # Start TLS for security
        print("Starting TLS...")
        server.starttls()
        
        # Authentication
        print("Authenticating...")
        server.login(SMTP_USER, SMTP_PASSWORD)
        
        # Prepare message
        message = f"Subject: {EMAIL_SUBJECT}\n\n{body}"
        message = message.encode('utf-8')  # Encode message as UTF-8
        
        # Send email
        print("Sending email...")
        server.sendmail(EMAIL_FROM, EMAIL_TO, message)
        print("Email sent successfully")
        
        # Close the connection
        server.quit()
        return True
        
    except smtplib.SMTPServerDisconnected as e:
        print(f"SMTP Server disconnected: {e}")
        return False
    except smtplib.SMTPAuthenticationError as e:
        print(f"SMTP Authentication failed: {e}")
        return False
    except Exception as e:
        print(f"Email error: {type(e).__name__}: {e}")
        return False

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
Device Details:
MAC: {mac}
IP: {ip}
Hostname: {hostname or 'Unknown'}
Vendor: {vendor or 'Unknown'}
Open Ports: {', '.join(map(str, ports)) if ports else 'None detected'}
    """.strip()

def check_for_unknown_devices():
    """Check for new devices and active unknown devices that need alerts."""
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cursor = conn.cursor()
        
        # Check for new devices that haven't been alerted on
        cursor.execute("""
            INSERT INTO alerts (device_id, alert_type, detected_at, details, severity)
            SELECT 
                nd.mac_address::macaddr,
                'new_device',
                nd.last_seen,
                CONCAT(
                    'New device detected:\n',
                    'MAC: ', nd.mac_address::macaddr::text, '\n',
                    'IP: ', COALESCE(nd.last_ip::text, 'Unknown'), '\n',
                    'First Seen: ', nd.first_seen, '\n',
                    CASE 
                        WHEN nd.device_name IS NOT NULL THEN CONCAT('Name: ', nd.device_name, '\n')
                        ELSE ''
                    END
                ),
                'medium'
            FROM new_devices nd
            LEFT JOIN known_devices kd ON kd.mac_address::macaddr = nd.mac_address::macaddr
            LEFT JOIN alerts a ON 
                a.device_id = nd.mac_address::macaddr AND 
                a.alert_type = 'new_device'
            WHERE kd.mac_address IS NULL  -- Ensure device is not in known_devices
            AND a.id IS NULL             -- Ensure we haven't alerted on this device before
            RETURNING device_id::text;
        """)
        new_device_alerts = cursor.fetchall()
        for alert in new_device_alerts:
            print(f"Created alert for new device: {alert[0]}")
            
        # Check for unknown devices that have been recently active
        cursor.execute("""
            WITH recent_activity AS (
                SELECT DISTINCT ON (ud.mac_address)
                    ud.mac_address,
                    dl.ip_address,
                    dl.timestamp,
                    ud.threat_level,
                    ud.notes,
                    ud.first_seen,
                    (
                        SELECT COUNT(*) 
                        FROM discovery_log 
                        WHERE mac_address::macaddr = ud.mac_address::macaddr
                    ) as detection_count
                FROM unknown_devices ud
                JOIN discovery_log dl ON dl.mac_address::macaddr = ud.mac_address::macaddr
                WHERE dl.timestamp > NOW() - INTERVAL '5 minutes'
                ORDER BY ud.mac_address, dl.timestamp DESC
            )
            SELECT 
                ra.mac_address,
                ra.ip_address,
                ra.timestamp,
                ra.threat_level,
                ra.notes,
                ra.first_seen,
                ra.detection_count
            FROM recent_activity ra
            LEFT JOIN alerts a ON 
                a.device_id::macaddr = ra.mac_address::macaddr AND 
                a.alert_type = 'unknown_device' AND 
                NOT a.is_resolved AND
                a.detected_at > NOW() - INTERVAL '1 hour'
            WHERE a.id IS NULL
        """)
        unknown_connections = cursor.fetchall()

        # Create alerts for unknown device connections
        for mac, ip, timestamp, threat_level, notes, first_seen, count in unknown_connections:
            # Update last_seen in unknown_devices
            cursor.execute("""
                UPDATE unknown_devices 
                SET last_seen = %s, last_ip = %s::inet 
                WHERE mac_address = %s::macaddr
            """, (timestamp, ip, mac))

            # Format basic alert details without hostname/vendor info
            device_info = format_device_info(mac, ip, None, None, [])
            alert_details = f"""
THREAT DETECTED: {threat_level.upper()} Risk Device
{device_info}

History:
First Seen: {first_seen}
Total Detections: {count}

Threat Notes: 
{notes}
            """.strip()

            # Check if we need to create a new alert
            try:
                cursor.execute("""
                    WITH latest_alert AS (
                        SELECT detected_at
                        FROM alerts
                        WHERE device_id::macaddr = %s::macaddr
                        AND alert_type = 'unknown_device'
                        AND NOT is_resolved
                        ORDER BY detected_at DESC
                        LIMIT 1
                    )
                    SELECT 
                        CASE 
                            WHEN latest_alert.detected_at IS NULL THEN true
                            WHEN latest_alert.detected_at < NOW() - INTERVAL '1 hour' THEN true
                            ELSE false
                        END as should_alert
                    FROM (SELECT true) as t
                    LEFT JOIN latest_alert ON true;
                """, (mac,))
                
                should_alert = cursor.fetchone()[0]
                
                if should_alert:
                    cursor.execute("""
                        INSERT INTO alerts (device_id, detected_at, alert_type, details, severity)
                        VALUES (%s::macaddr, %s, 'unknown_device', %s, %s)
                        RETURNING device_id::text
                    """, (mac, timestamp, alert_details, threat_level))
                    alert_mac = cursor.fetchone()[0]
                    print(f"New alert created for device: {alert_mac}")
                else:
                    print(f"Skipping alert creation for {mac} - recent alert exists")
                    
            except psycopg2.Error as e:
                print(f"Error handling alert for {mac}: {e}")

        conn.commit()
        cursor.close()
        conn.close()
    except Exception as e:
        print(f"Error checking unknown devices: {e}")

last_email_time = None
email_cooldown = 300  # 5 minutes between email attempts

def check_alerts():
    global last_email_time
    
    # Check if we're still in cooldown period
    current_time = time.time()
    if last_email_time and (current_time - last_email_time) < email_cooldown:
        print(f"Email cooldown active. Waiting {email_cooldown - (current_time - last_email_time):.0f} seconds...")
        return
        
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cursor = conn.cursor()
        
        # First, check if we have any unresolved alerts that need attention
        cursor.execute("""
            SELECT COUNT(*) 
            FROM alerts 
            WHERE NOT is_resolved 
            AND alert_type IN ('unknown_device', 'new_device')
            AND detected_at > NOW() - INTERVAL '1 hour'
        """)
        alert_count = cursor.fetchone()[0]
        
        if alert_count == 0:
            return
            
        # Get only the most recent alerts for each device
        cursor.execute("""
            WITH latest_alerts AS (
                SELECT DISTINCT ON (device_id) 
                    id,
                    device_id,
                    detected_at,
                    alert_type,
                    details,
                    severity
                FROM alerts 
                WHERE NOT is_resolved 
                AND alert_type IN ('unknown_device', 'new_device')
                AND detected_at > NOW() - INTERVAL '1 hour'
                ORDER BY device_id, detected_at DESC
            )
            SELECT * FROM latest_alerts
            ORDER BY 
                severity DESC,
                CASE alert_type 
                    WHEN 'unknown_device' THEN 1
                    WHEN 'new_device' THEN 2
                    ELSE 3
                END,
                detected_at DESC
        """)
        rows = cursor.fetchall()
        
        max_retries = 3
        for alert_id, device_id, timestamp, alert_type, details, severity in rows:
            # Format message based on alert type
            if alert_type == 'new_device':
                body = f"NEW Device Detected\nMAC: {device_id}\nTime: {timestamp}\nDetails: {details}"
            elif alert_type == 'unknown_device':
                body = f"ALERT: {severity.upper()} Risk Threat Device Connected\n{details}\nDetected at: {timestamp}"
            else:
                continue  # Skip other alert types
            
            # Try to send email with retries
            for retry in range(max_retries):
                if send_email(body):
                    cursor.execute("""
                        UPDATE alerts 
                        SET is_resolved = TRUE,
                            resolved_at = NOW(),
                            resolution_notes = 'Alert sent successfully'
                        WHERE id = %s
                    """, (alert_id,))
                    conn.commit()
                    break
                else:
                    if retry < max_retries - 1:
                        print(f"Retrying email in 5 seconds... (Attempt {retry + 1}/{max_retries})")
                        time.sleep(5)
                    else:
                        print(f"Failed to send alert after {max_retries} attempts")

        conn.commit()
        cursor.close()
        conn.close()

    except Exception as e:
        print(f"Database error: {e}")

if __name__ == "__main__":
    print("Alert daemon started...")
    while True:
        check_for_unknown_devices()  # Check for unknown device connections
        check_alerts()               # Process pending alerts
        time.sleep(10)  # Check every 10 seconds
