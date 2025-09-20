from ..logging.logger import setup_logging
from .handlers import DeviceHandler
from .notifiers.email import EmailNotifier
from .notifiers.telegram import TelegramNotifier
import time

logger = setup_logging('netureon.daemon')

class AlertDaemon:
    def __init__(self):
        self.device_handler = DeviceHandler()
        self.email_notifier = EmailNotifier()
        self.telegram_notifier = TelegramNotifier()
        self.running = True
        self.check_interval = 10  # seconds

    def run(self):
        """Main daemon loop."""
        logger.info("Alert daemon started")
        
        while self.running:
            try:
                # Check for new devices
                new_devices = self.device_handler.check_for_unknown_devices()
                
                for mac, ip, timestamp in new_devices:
                    alert_id = self.device_handler.profile_device(mac, ip, timestamp)
                    if alert_id:
                        self._send_notifications(alert_id)
                        
                time.sleep(self.check_interval)
                
            except Exception as e:
                logger.error(f"Error in main loop: {str(e)}")
                time.sleep(30)  # Wait longer on error

    def _send_notifications(self, alert_id):
        """Send notifications for an alert."""
        try:
            alert = self.device_handler.get_alert(alert_id)
            if not alert:
                return
                
            subject = f"NetGuard Alert: {alert['type']}"
            body = alert['details']
            
            email_sent = self.email_notifier.send_notification(subject, body)
            telegram_sent = self.telegram_notifier.send_notification(body)
            
            self.device_handler.update_alert_status(
                alert_id, 
                email_sent, 
                telegram_sent
            )
            
        except Exception as e:
            logger.error(f"Error sending notifications: {str(e)}")