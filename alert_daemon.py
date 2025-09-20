import psycopg2
import smtplib
import requests
import time
import os
from datetime import datetime, timedelta
import logging
from logging.handlers import RotatingFileHandler
from device_profiler import DeviceProfiler
from webui.models.config import Configuration

# Set up logging
def setup_logging():
    log_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'logs')
    os.makedirs(log_dir, exist_ok=True)
    
    log_file = os.path.join(log_dir, 'alert_daemon.log')
    
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
    
    logger = logging.getLogger('netureon')
    logger.setLevel(logging.INFO)
    
    # Remove any existing handlers
    logger.handlers = []
    
    logger.addHandler(handler)
    return logger

logger = setup_logging()

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

def send_email(subject, body):
    """Send email notification with improved error handling."""
    settings = get_notification_settings()
    logger.info("Attempting to send email notification...")
    
    if settings['enable_email_notifications'] != 'true':
        logger.info("Email notifications are disabled in settings")
        return False
    
    required_settings = [
        'smtp_server', 'smtp_port', 'smtp_username', 'smtp_password',
        'smtp_from_address', 'smtp_to_address'
    ]
    
    missing = [s for s in required_settings if not settings.get(s)]
    if missing:
        logger.error(f"Email configuration incomplete. Missing: {', '.join(missing)}")
        return False
        
    try:
        logger.debug(f"Connecting to SMTP server {settings['smtp_server']}:{settings['smtp_port']}")
        server = smtplib.SMTP(settings['smtp_server'], int(settings['smtp_port']))
        
        # Start TLS for security
        server.starttls()
        
        # Authentication
        logger.debug("Authenticating with SMTP server...")
        server.login(settings['smtp_username'], settings['smtp_password'])
        
        # Prepare message with proper headers
        message = f"""From: NetGuard <{settings['smtp_from_address']}>
To: <{settings['smtp_to_address']}>
Subject: {subject}

{body}"""
        message = message.encode('utf-8')
        
        # Send email
        server.sendmail(settings['smtp_from_address'], 
                       settings['smtp_to_address'], 
                       message)
        logger.info("Email sent successfully")
        
        server.quit()
        return True
        
    except Exception as e:
        logger.error(f"Failed to send email: {str(e)}")
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
    """Check for new devices and profile them."""
    logger.info("=== Starting device check cycle ===")
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cursor = conn.cursor()
        
        # Get only truly new devices without profiles
        logger.info("Querying for new devices...")
        cursor.execute("""
            SELECT DISTINCT ON (nd.mac_address)
                nd.mac_address::text,
                nd.last_ip::text,
                nd.last_seen
            FROM new_devices nd
            LEFT JOIN alerts a ON a.device_id = nd.mac_address
            WHERE a.id IS NULL
            AND nd.last_seen > NOW() - INTERVAL '5 minutes'
        """)
        
        new_devices = cursor.fetchall()
        if new_devices:
            logger.info(f"Found {len(new_devices)} new devices to process:")
            for mac, ip, _ in new_devices:
                logger.info(f"  • MAC: {mac}, IP: {ip}")
            
            profiler = DeviceProfiler()
            logger.info("Starting device profiling process...")
            
            for mac, ip, timestamp in new_devices:
                try:
                    logger.info(f"\nProcessing device: MAC={mac}, IP={ip}")
                    logger.info("1. Starting device profiling...")
                    profile = profiler.profile_device(ip, mac)
                    
                    if profile:
                        logger.info("2. Profile results:")
                        logger.info(f"   • Hostname: {profile.get('hostname', 'Unknown')}")
                        logger.info(f"   • Vendor: {profile.get('vendor', 'Unknown')}")
                        logger.info(f"   • Type: {profile.get('device_type', 'Unknown')}")
                        logger.info(f"   • Open Ports: {profile.get('open_ports', [])}")
                        
                        # Store profile
                        logger.info("3. Storing device profile...")
                        ports_json = json.dumps(profile.get('open_ports', []))
                        cursor.execute("""
                            INSERT INTO device_profiles 
                            (mac_address, hostname, vendor, device_type, open_ports, last_updated)
                            VALUES (%s::macaddr, %s, %s, %s, %s::jsonb, NOW())
                            ON CONFLICT (mac_address) DO UPDATE SET
                                hostname = EXCLUDED.hostname,
                                vendor = EXCLUDED.vendor,
                                device_type = EXCLUDED.device_type,
                                open_ports = EXCLUDED.open_ports,
                                last_updated = NOW()
                        """, (
                            mac,
                            profile.get('hostname', 'Unknown'),
                            profile.get('vendor', 'Unknown'),
                            profile.get('device_type', 'Unknown'),
                            ports_json
                        ))
                        
                        # Create alert with profile info
                        logger.info("4. Creating alert...")
                        details = f"""New device detected:
MAC: {mac}
IP: {ip}
Hostname: {profile.get('hostname', 'Unknown')}
Vendor: {profile.get('vendor', 'Unknown')}
Type: {profile.get('device_type', 'Unknown')}
Open Ports: {', '.join(str(p['port']) for p in profile.get('open_ports', []))}"""

                        cursor.execute("""
                            INSERT INTO alerts 
                            (device_id, alert_type, detected_at, details, severity, is_resolved)
                            VALUES (%s::macaddr, 'new_device', NOW(), %s, 'medium', false)
                            RETURNING id
                        """, (mac, details))
                        
                        alert_id = cursor.fetchone()[0]
                        conn.commit()
                        logger.info(f"   • Alert created with ID: {alert_id}")
                        
                        # Send notifications
                        logger.info("5. Sending notifications...")
                        email_sent = send_email("NetGuard Alert: New Device Detected", details)
                        logger.info(f"   • Email notification: {'✓' if email_sent else '✗'}")
                        
                        telegram_sent = send_telegram(details)
                        logger.info(f"   • Telegram notification: {'✓' if telegram_sent else '✗'}")
                        
                        logger.info(f"Device {mac} processing completed successfully")
                    else:
                        logger.error(f"Profile results empty for device {mac}")
                    
                except Exception as e:
                    logger.error(f"Error processing device {mac}:")
                    logger.error(f"Error details: {str(e)}")
                    conn.rollback()
                    continue

        else:
            logger.info("No new devices found requiring profiling")

    except Exception as e:
        logger.error(f"Error in check_for_unknown_devices: {str(e)}")
        if 'conn' in locals():
            conn.rollback()
    finally:
        if 'cursor' in locals():
            cursor.close()
        if 'conn' in locals():
            conn.close()
        logger.info("=== Device check cycle completed ===\n")

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
                detected_at DESC
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
