from ..logging.logger import setup_logging
from ..config.settings import Settings
from .handlers import DeviceHandler
from .notifiers.email import EmailNotifier
from .notifiers.telegram import TelegramNotifier
import time
import psycopg2
from datetime import datetime, timedelta

logger = setup_logging('netureon.daemon')

class AlertDaemon:
    def __init__(self):
        self.db_config = Settings.get_db_config()
        self.device_handler = DeviceHandler()
        self.email_notifier = EmailNotifier()
        self.telegram_notifier = TelegramNotifier()
        self.last_email_time = None
        self.email_cooldown = 300

    def check_for_unknown_devices(self):
        """Check and process new devices."""
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
                        LEFT JOIN alerts a ON a.device_id = nd.mac_address 
                            AND a.alert_type = 'new_device'
                            AND a.detected_at > NOW() - INTERVAL '1 hour'
                        WHERE dp.mac_address IS NULL
                            AND a.id IS NULL
                            AND nd.last_seen > NOW() - INTERVAL '5 minutes'
                    """)
                    
                    new_devices = cursor.fetchall()
                    if new_devices:
                        logger.info(f"Found {len(new_devices)} new devices to process:")
                        for mac, ip, timestamp in new_devices:
                            logger.info(f"Processing device: MAC={mac}, IP={ip}")
                            
                            # Profile and create alert
                            alert_id = self.device_handler.process_new_device(mac, ip, timestamp)
                            
                            if alert_id:
                                # Get alert details
                                cursor.execute("""
                                    SELECT details FROM alerts WHERE id = %s
                                """, (alert_id,))
                                details = cursor.fetchone()[0]
                                
                                # Send notifications
                                subject = "NetGuard Alert: New Device Detected"
                                email_sent = self.email_notifier.send_notification(subject, details)
                                telegram_sent = self.telegram_notifier.send_notification(details)
                                
                                logger.info(f"Notifications for {mac}:")
                                logger.info(f"  • Email: {'✓' if email_sent else '✗'}")
                                logger.info(f"  • Telegram: {'✓' if telegram_sent else '✗'}")
                    else:
                        logger.debug("No new devices requiring profiling")
                        
        except Exception as e:
            logger.error(f"Error checking for unknown devices: {str(e)}")

    def process_pending_alerts(self):
        """Process any pending alerts."""
        try:
            current_time = time.time()
            if self.last_email_time and (current_time - self.last_email_time) < self.email_cooldown:
                return

            with psycopg2.connect(**self.db_config) as conn:
                with conn.cursor() as cursor:
                    cursor.execute("""
                        SELECT 
                            id, device_id, alert_type, 
                            detected_at, details, severity
                        FROM alerts 
                        WHERE NOT is_resolved 
                            AND detected_at > NOW() - INTERVAL '1 hour'
                        ORDER BY severity DESC, detected_at DESC
                    """)
                    
                    pending_alerts = cursor.fetchall()
                    if pending_alerts:
                        logger.info(f"Processing {len(pending_alerts)} pending alerts")
                        
                        for alert in pending_alerts:
                            alert_id, device_id, alert_type, detected_at, details, severity = alert
                            
                            # Send notifications
                            subject = f"NetGuard Alert: {severity.upper()} - {alert_type}"
                            email_sent = self.email_notifier.send_notification(subject, details)
                            telegram_sent = self.telegram_notifier.send_notification(details)
                            
                            if email_sent or telegram_sent:
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
                                
                                if email_sent:
                                    self.last_email_time = current_time
                                    
                            logger.info(f"Processed alert {alert_id} for device {device_id}")
                    
        except Exception as e:
            logger.error(f"Error processing pending alerts: {str(e)}")

    def run(self):
        """Main daemon loop."""
        logger.info("Alert daemon started...")
        while True:
            try:
                self.check_for_unknown_devices()
                self.process_pending_alerts()
                time.sleep(10)
            except Exception as e:
                logger.error(f"Error in main loop: {str(e)}")
                time.sleep(30)  # Wait longer on error