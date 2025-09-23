from ..logging.logger import setup_logging
from ..config.settings import Settings
from device_profiler import DeviceProfiler
import psycopg2
import json

logger = setup_logging('netureon.handlers')

class DeviceHandler:
    def __init__(self):
        self.settings = Settings.get_instance()
        self.db_config = self.settings.get_db_config()
        self.profiler = DeviceProfiler()
        self.logger = logger  # Use module-level logger

    def check_for_unknown_devices(self):
        """Check and profile new devices."""
        logger.info("=== Starting device check cycle ===")
        try:
            with psycopg2.connect(**self.db_config) as conn:
                with conn.cursor() as cursor:
                    # Get only new devices without profiles
                    cursor.execute("""
                        SELECT DISTINCT ON (nd.mac_address)
                            nd.mac_address::text,
                            nd.last_ip::text,
                            nd.last_seen
                        FROM new_devices nd
                        LEFT JOIN device_profiles dp ON dp.mac_address = nd.mac_address
                        LEFT JOIN alerts a ON a.device_mac = nd.mac_address 
                        WHERE dp.mac_address IS NULL
                        AND a.id IS NULL
                        AND nd.last_seen > NOW() - INTERVAL '5 minutes'
                    """)
                    
                    new_devices = cursor.fetchall()
                    return new_devices if new_devices else []
                    
        except Exception as e:
            logger.error(f"Error checking for unknown devices: {str(e)}")
            return []

    def store_device_profile(self, mac, profile):
        """Store device profile in database."""
        try:
            with psycopg2.connect(**self.db_config) as conn:
                with conn.cursor() as cursor:
                    cursor.execute("""
                        UPDATE new_devices 
                        SET hostname = %s,
                            vendor = %s,
                            device_type = %s,
                            open_ports = %s::jsonb,
                            last_updated = NOW()
                        WHERE mac_address = %s::macaddr
                    """, (
                        profile.get('hostname', 'Unknown'),
                        profile.get('vendor', 'Unknown'),
                        profile.get('device_type', 'Unknown'),
                        json.dumps(profile.get('open_ports', [])),
                        mac
                    ))
                    conn.commit()
                    self.logger.info(f"Stored profile for device {mac}")
        except Exception as e:
            self.logger.error(f"Failed to store profile for {mac}: {e}")

    def profile_device(self, mac, ip, timestamp):
        """Profile a device and send notifications."""
        try:
            profile = self.profiler.profile_device(ip, mac)
            if profile:
                # Store profile
                self.store_device_profile(mac, profile)
                
                # Create alert with profile info
                details = f"""New device detected:
MAC: {mac}
IP: {ip}
Hostname: {profile.get('hostname', 'Unknown')}
Vendor: {profile.get('vendor', 'Unknown')}
Type: {profile.get('device_type', 'Unknown')}
Open Ports: {', '.join(f"{p['port']} ({p['service']})" for p in profile.get('open_ports', []))}"""

                alert_id = self.create_alert(mac, ip, details, timestamp)
                
                # Send notifications immediately
                if alert_id:
                    self.send_notifications(
                        alert_id, 
                        "NetGuard Alert: New Device Detected", 
                        details
                    )
                
                return alert_id
            
            return None
            
        except Exception as e:
            self.logger.error(f"Error profiling device {mac}: {e}")
            return None

    def create_alert(self, mac, ip, details, timestamp):
        """Create an alert for the detected device."""
        try:
            with psycopg2.connect(**self.db_config) as conn:
                with conn.cursor() as cursor:
                    cursor.execute("""
                        INSERT INTO alerts 
                        (device_mac, alert_type, detected_at, details, severity)
                        VALUES (%s::macaddr, 'new_device', NOW(), %s, 'medium')
                        RETURNING id
                    """, (mac, details))
                    
                    alert_id = cursor.fetchone()[0]
                    conn.commit()
                    self.logger.info(f"Created alert {alert_id} for device {mac}")
                    return alert_id
                    
        except Exception as e:
            self.logger.error(f"Error creating alert for device {mac}: {e}")
            return None

    def get_alert(self, alert_id):
        """Get alert details by ID."""
        try:
            with psycopg2.connect(**self.db_config) as conn:
                with conn.cursor() as cursor:
                    cursor.execute("""
                        SELECT 
                            device_mac,
                            alert_type,
                            detected_at,
                            details,
                            severity
                        FROM alerts 
                        WHERE id = %s
                    """, (alert_id,))
                    
                    row = cursor.fetchone()
                    if row:
                        return {
                            'id': alert_id,
                            'device_mac': row[0],
                            'type': row[1],
                            'timestamp': row[2],
                            'details': row[3],
                            'severity': row[4]
                        }
                    return None
                    
        except Exception as e:
            logger.error(f"Error getting alert {alert_id}: {str(e)}")
            return None

    def update_alert_status(self, alert_id, email_sent, telegram_sent):
        """Update alert status after sending notifications."""
        try:
            with psycopg2.connect(**self.db_config) as conn:
                with conn.cursor() as cursor:
                    cursor.execute("""
                        UPDATE alerts 
                        SET is_resolved = true,
                            resolved_at = NOW(),
                            resolution_notes = %s
                        WHERE id = %s
                    """, (
                        f"Notifications sent - Email: {'✓' if email_sent else '✗'}, "
                        f"Telegram: {'✓' if telegram_sent else '✗'}",
                        alert_id
                    ))
                    conn.commit()
                    
        except Exception as e:
            logger.error(f"Error updating alert {alert_id}: {str(e)}")

    def send_notifications(self, alert_id, subject, message):
        """Send notifications for an alert."""
        try:
            settings = Settings.get_instance()
            notification_settings = settings.get_notification_settings()
            
            # Send email if enabled
            email_sent = False
            if notification_settings.get('enable_email_notifications'):
                from ..alerts.notifiers.email import EmailNotifier
                email_notifier = EmailNotifier()
                email_sent = email_notifier.send_notification(subject, message)
                self.logger.info(f"Email notification {'sent' if email_sent else 'failed'}")

            # Send Telegram if enabled
            telegram_sent = False
            if notification_settings.get('enable_telegram_notifications'):
                from ..alerts.notifiers.telegram import TelegramNotifier
                telegram_notifier = TelegramNotifier()
                telegram_sent = telegram_notifier.send_notification(message)
                self.logger.info(f"Telegram notification {'sent' if telegram_sent else 'failed'}")

            # Update alert status
            self.update_alert_status(alert_id, email_sent, telegram_sent)
                
        except Exception as e:
            self.logger.error(f"Error sending notifications: {str(e)}")