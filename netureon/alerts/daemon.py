from ..logging.logger import setup_logging
from ..config.settings import Settings
from .handlers import DeviceHandler
from .notifiers.telegram import TelegramNotifier
from .notifiers.email import EmailNotifier
import time
import os
import subprocess
from pathlib import Path

logger = setup_logging('netureon.daemon')

class AlertDaemon:
    def __init__(self):
        self.settings = Settings.get_instance()
        self._check_dependencies()
        self.device_handler = DeviceHandler()
        self.email_notifier = EmailNotifier()
        self.telegram_notifier = TelegramNotifier()
        self.running = True
        self.check_interval = 30  # seconds

    def _find_nmap(self):
        """Find nmap executable in system paths."""
        possible_paths = [
            '/usr/bin/nmap',
            '/usr/local/bin/nmap',
            '/bin/nmap',
            '/usr/sbin/nmap'
        ]
        
        for path in possible_paths:
            if os.path.isfile(path) and os.access(path, os.X_OK):
                return path
        return None

    def _check_dependencies(self):
        """Check if required system dependencies are available."""
        try:
            # Try to find nmap executable
            nmap_path = self._find_nmap()
            if not nmap_path:
                raise FileNotFoundError("nmap executable not found in system paths")

            # Test nmap execution
            result = subprocess.run(
                [nmap_path, '--version'],
                capture_output=True,
                text=True
            )
            if result.returncode != 0:
                raise subprocess.CalledProcessError(
                    result.returncode, 
                    [nmap_path, '--version']
                )

            logger.info(f"Found nmap at: {nmap_path}")
            # Store path for later use
            os.environ['NMAP_PATH'] = nmap_path
            
        except FileNotFoundError as e:
            logger.error(f"nmap not found: {str(e)}")
            logger.error("Please install nmap: sudo apt-get install nmap")
            raise SystemError("Required dependency 'nmap' not found")
        except subprocess.CalledProcessError as e:
            logger.error(f"nmap check failed: {str(e)}")
            logger.error(f"Command output: {e.output}")
            raise SystemError("nmap is not working properly")
        except Exception as e:
            logger.error(f"Unexpected error checking dependencies: {str(e)}")
            raise

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