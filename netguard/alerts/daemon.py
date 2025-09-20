from ..logging.logger import setup_logging
from ..config.settings import Settings
from .handlers import DeviceHandler
from .notifiers.email import EmailNotifier
from .notifiers.telegram import TelegramNotifier
import time
import psycopg2

logger = setup_logging('netureon.daemon')

class AlertDaemon:
    def __init__(self):
        self.db_config = Settings.get_db_config()
        self.device_handler = DeviceHandler()
        self.email_notifier = EmailNotifier()
        self.telegram_notifier = TelegramNotifier()
        self.last_email_time = None
        self.email_cooldown = 300

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