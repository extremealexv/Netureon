import psycopg2
import smtplib
import requests
import time
import os
from datetime import datetime, timedelta
import logging
from device_profiler import DeviceProfiler
from webui.models.config import Configuration

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

# Initialize Flask app to access configuration
from webui.app import create_app
app = create_app()

def get_notification_settings():
    """Get notification settings from the database."""
    with app.app_context():
        settings = {
            'enable_email_notifications': Configuration.get_setting('enable_email_notifications'),
            'enable_telegram_notifications': Configuration.get_setting('enable_telegram_notifications'),
            'smtp_server': Configuration.get_setting('smtp_server'),
            'smtp_port': Configuration.get_setting('smtp_port', '587'),
            'smtp_username': Configuration.get_setting('smtp_username'),
            'smtp_password': Configuration.get_setting('smtp_password'),
            'smtp_from_address': Configuration.get_setting('smtp_from_address'),
            'smtp_to_address': Configuration.get_setting('smtp_to_address'),
            'telegram_bot_token': Configuration.get_setting('telegram_bot_token'),
            'telegram_chat_id': Configuration.get_setting('telegram_chat_id')
        }
    return settings

def get_scan_config():
    """Get scanning configuration from database."""
    with app.app_context():
        return {
            'port_scan_timeout': int(Configuration.get_setting('port_scan_timeout', '2')),
            'max_ports': int(Configuration.get_setting('max_ports', '1000')),
            'interface': Configuration.get_setting('network_interface', 'eth0')
        }

def send_email(body):
    settings = get_notification_settings()
    
    # First check if email notifications are enabled
    if settings['enable_email_notifications'] != 'true':
        print("Email notifications are disabled in NetGuard settings")
        return False
    
    # Check if all required settings are present
    required_settings = [
        'smtp_server', 'smtp_port', 'smtp_username', 'smtp_password',
        'smtp_from_address', 'smtp_to_address'
    ]
    
    missing = [s for s in required_settings if not settings.get(s)]
    if missing:
        print(f"Email configuration incomplete. Missing: {', '.join(missing)}")
        return False
        
    try:
        print(f"Attempting to send email notification to {settings['smtp_to_address']}")
        server = smtplib.SMTP(settings['smtp_server'], int(settings['smtp_port']))
        server.set_debuglevel(1)  # Enable debug output
        
        # Start TLS for security
        print("Starting TLS...")
        server.starttls()
        
        # Authentication
        print("Authenticating...")
        server.login(settings['smtp_username'], settings['smtp_password'])
        
        # Prepare message
        message = f"Subject: NetGuard Alert\n\n{body}"
        message = message.encode('utf-8')  # Encode message as UTF-8
        
        # Send email
        print("Sending email...")
        server.sendmail(settings['smtp_from_address'], settings['smtp_to_address'], message)
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

def send_telegram(message):
    settings = get_notification_settings()
    
    # First check if telegram notifications are enabled
    if settings['enable_telegram_notifications'] != 'true':
        print("Telegram notifications are disabled in NetGuard settings")
        return False
        
    # Check if telegram is configured
    if not settings.get('telegram_bot_token') or not settings.get('telegram_chat_id'):
        print("Telegram configuration incomplete")
        return False
        
    try:
        url = f"https://api.telegram.org/bot{settings['telegram_bot_token']}/sendMessage"
        payload = {"chat_id": settings['telegram_chat_id'], "text": message}
        response = requests.post(url, data=payload)
        response.raise_for_status()
        return True
    except Exception as e:
        print(f"Telegram error: {e}")
        return False

def format_device_info(mac, ip, hostname, vendor, ports):
    """Format device information for alerts with enhanced profiling."""
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cursor = conn.cursor()
        
        # Get full device profile
        cursor.execute("""
            SELECT 
                dp.hostname,
                dp.vendor,
                dp.device_type,
                dp.open_ports,
                dp.last_updated
            FROM device_profiles dp
            WHERE dp.mac_address = %s::macaddr
        """, (mac,))
        
        profile = cursor.fetchone()
        
        if profile:
            hostname, vendor, device_type, open_ports, last_updated = profile
            return f"""
Device Details:
MAC: {mac}
IP: {ip}
Hostname: {hostname or 'Unknown'}
Vendor: {vendor or 'Unknown'}
Device Type: {device_type or 'Unknown'}
Open Ports: {', '.join(map(str, open_ports)) if open_ports else 'None detected'}
Last Profiled: {last_updated}
            """.strip()
        else:
            # If no profile exists, return basic info
            return f"""
Device Details:
MAC: {mac}
IP: {ip}
Status: Profiling in progress...
            """.strip()
            
    except Exception as e:
        print(f"Error formatting device info: {e}")
        return f"Device: {mac} (IP: {ip})"
    finally:
        if 'cursor' in locals():
            cursor.close()
        if 'conn' in locals():
            conn.close()

def check_for_unknown_devices():
    """Check for new devices and active unknown devices that need alerts."""
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cursor = conn.cursor()
        
        # Check for new devices and profile them
        cursor.execute("""
            WITH new_unidentified AS (
                SELECT 
                    nd.mac_address,
                    nd.last_ip,
                    nd.last_seen
                FROM new_devices nd
                LEFT JOIN device_profiles dp ON dp.mac_address = nd.mac_address
                WHERE dp.mac_address IS NULL  -- Only get devices without profiles
                AND nd.last_seen > NOW() - INTERVAL '5 minutes'
            )
            SELECT 
                mac_address::text,
                last_ip::text,
                last_seen
            FROM new_unidentified
        """)
        
        new_devices = cursor.fetchall()
        
        # Profile new devices
        profiler = DeviceProfiler()
        
        for mac, ip, timestamp in new_devices:
            try:
                # Get device profile
                profile = profiler.profile_device(ip)
                
                if profile:
                    # Update device profile in database
                    cursor.execute("""
                        INSERT INTO device_profiles 
                        (mac_address, hostname, vendor, device_type, open_ports, last_updated)
                        VALUES (%s::macaddr, %s, %s, %s, %s::jsonb, NOW())
                        ON CONFLICT (mac_address) 
                        DO UPDATE SET
                            hostname = EXCLUDED.hostname,
                            vendor = EXCLUDED.vendor,
                            device_type = EXCLUDED.device_type,
                            open_ports = EXCLUDED.open_ports,
                            last_updated = NOW()
                    """, (
                        mac,
                        profile.get('hostname'),
                        profile.get('vendor'),
                        profile.get('device_type'),  # Fixed missing parenthesis
                        profile.get('open_ports', '[]')
                    ))
                    conn.commit()
                    print(f"Updated profile for device {mac}")
            
            except Exception as e:
                print(f"Error profiling device {mac}: {e}")
                continue

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
    """Check and process pending alerts."""
    global last_email_time
    
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cursor = conn.cursor()
        
        current_time = time.time()
        
        # Check if we're still in cooldown period
        if last_email_time and (current_time - last_email_time) < email_cooldown:
            logger.debug(f"Email cooldown active. Waiting {email_cooldown - (current_time - last_email_time):.0f} seconds...")
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
            ORDER BY severity DESC,
                CASE alert_type 
                    WHEN 'unknown_device' THEN 1
                    WHEN 'new_device' THEN 2
                    ELSE 3
                END,
                detected_at DESC;
        """)
        
        rows = cursor.fetchall()
        
        if not rows:
            logger.debug("No pending alerts found")
            return
            
        for alert_id, device_id, timestamp, alert_type, details, severity in rows:
            try:
                # Format message based on alert type
                if alert_type == 'new_device':
                    subject = "NetGuard Alert: New Device Detected"
                    body = f"NEW Device Detected\nMAC: {device_id}\nTime: {timestamp}\nDetails: {details}"
                elif alert_type == 'unknown_device':
                    subject = f"NetGuard Alert: {severity.upper()} Risk Device"
                    body = f"ALERT: {severity.upper()} Risk Threat Device Connected\n{details}\nDetected at: {timestamp}"
                else:
                    continue
                
                # Send notifications
                email_sent = send_email(subject, body)
                telegram_sent = send_telegram(body)
                
                if email_sent or telegram_sent:
                    # Mark alert as resolved if at least one notification was sent
                    cursor.execute("""
                        UPDATE alerts 
                        SET is_resolved = TRUE,
                            resolved_at = NOW(),
                            resolution_notes = %s
                        WHERE id = %s
                    """, (
                        f"Notifications sent - Email: {'✓' if email_sent else '✗'}, Telegram: {'✓' if telegram_sent else '✗'}",
                        alert_id
                    ))
                    conn.commit()
                    
                    if email_sent:
                        last_email_time = current_time
                
            except Exception as e:
                logger.error(f"Error processing alert {alert_id}: {str(e)}")
                continue
                
    except Exception as e:
        logger.error(f"Error checking alerts: {str(e)}")
    finally:
        if 'cursor' in locals():
            cursor.close()
        if 'conn' in locals():
            conn.close()

def handle_new_device(device_info):
    """Handle new device detection with proper logging"""
    logger = logging.getLogger('netureon')
    try:
        notifications_sent = []
        # Try email notification
        email_notifier = EmailNotifier()
        if email_notifier.config:
            email_sent = email_notifier.notify_new_device(
                device_info['mac'],
                device_info['ip'],
                device_info['timestamp']
            )
            notifications_sent.append(f"Email: {'✓' if email_sent else '✗'}")
        
        # Try Telegram notification
        telegram_notifier = TelegramNotifier()
        if telegram_notifier.config:
            telegram_sent = telegram_notifier.notify_new_device(
                device_info['mac'],
                device_info['ip'],
                device_info['timestamp']
            )
            notifications_sent.append(f"Telegram: {'✓' if telegram_sent else '✗'}")
        
        if notifications_sent:
            logger.info(f"Notifications sent: {', '.join(notifications_sent)}")
        else:
            logger.warning("No notification methods configured")
            
    except Exception as e:
        logger.error(f"Error in notification handler: {str(e)}")

if __name__ == "__main__":
    print("Alert daemon started...")
    while True:
        check_for_unknown_devices()  # Check for unknown device connections
        check_alerts()               # Process pending alerts
        time.sleep(10)  # Check every 10 seconds
