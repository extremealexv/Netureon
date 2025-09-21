import logging
from ..models.database import Database
import smtplib
from email.mime.text import MIMEText
import requests

class Notifier:
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self._settings = None

    @property
    def settings(self):
        """Get settings from database, cache for subsequent calls"""
        try:
            if self._settings is None:
                result = Database.execute_query("""
                    SELECT 
                        enable_telegram_notifications, 
                        enable_email_notifications,
                        telegram_bot_token,
                        telegram_chat_id,
                        smtp_server,
                        smtp_port,
                        smtp_username,
                        smtp_password,
                        notification_email
                    FROM settings
                    LIMIT 1
                """)
                self._settings = result[0] if result else None
                # Add detailed debug logging
                if self._settings:
                    self.logger.debug("Settings loaded:")
                    self.logger.debug(f"Telegram enabled: {self._settings['enable_telegram_notifications']}")
                    self.logger.debug(f"Email enabled: {self._settings['enable_email_notifications']}")
                    self.logger.debug(f"Telegram token exists: {bool(self._settings['telegram_bot_token'])}")
                    self.logger.debug(f"Telegram chat ID exists: {bool(self._settings['telegram_chat_id'])}")
                    self.logger.debug(f"SMTP server: {self._settings['smtp_server']}")
                    self.logger.debug(f"SMTP port: {self._settings['smtp_port']}")
                else:
                    self.logger.error("No settings found in database")
            return self._settings
        except Exception as e:
            self.logger.error(f"Error loading settings: {str(e)}")
            return None

    def send_notification(self, subject, message, notification_type="info"):
        """Send notification via configured channels."""
        self.logger.debug(f"Attempting to send notification: {subject}")
        self.logger.debug(f"Message: {message}")
        
        if not self.settings:
            self.logger.error("No notification settings found")
            return False

        success = False
        errors = []

        # Try Telegram notification with better error handling
        if self.settings.get('enable_telegram_notifications'):
            self.logger.debug("Telegram notifications are enabled")
            try:
                self._send_telegram(f"{subject}\n\n{message}")
                success = True
                self.logger.info("Telegram notification sent successfully")
            except Exception as e:
                error_msg = f"Telegram notification failed: {str(e)}"
                self.logger.error(error_msg)
                self.logger.exception(e)  # This will log the full stack trace
                errors.append(error_msg)

        # Try Email notification with better error handling
        if self.settings.get('enable_email_notifications'):
            self.logger.debug("Email notifications are enabled")
            try:
                self._send_email(subject, message)
                success = True
                self.logger.info("Email notification sent successfully")
            except Exception as e:
                error_msg = f"Email notification failed: {str(e)}"
                self.logger.error(error_msg)
                self.logger.exception(e)  # This will log the full stack trace
                errors.append(error_msg)

        if not success:
            error_message = " | ".join(errors) if errors else "No notification channels succeeded"
            self.logger.error(f"All notification attempts failed: {error_message}")
            raise Exception(error_message)

        return success

    def _send_telegram(self, message):
        """Send notification via Telegram."""
        if not self.settings.get('telegram_bot_token') or not self.settings.get('telegram_chat_id'):
            raise ValueError("Telegram credentials not configured")

        self.logger.debug("Sending Telegram message")
        url = f"https://api.telegram.org/bot{self.settings['telegram_bot_token']}/sendMessage"
        data = {
            "chat_id": self.settings['telegram_chat_id'],
            "text": message,
            "parse_mode": "HTML"
        }

        response = requests.post(url, json=data)
        if not response.ok:
            raise Exception(f"Telegram API error: {response.text}")

    def _send_email(self, subject, message):
        """Send notification via Email."""
        required_settings = [
            'smtp_server', 'smtp_port', 'smtp_username', 
            'smtp_password', 'notification_email'
        ]
        
        missing = [s for s in required_settings if not self.settings.get(s)]
        if missing:
            raise ValueError(f"Missing email settings: {', '.join(missing)}")

        self.logger.debug(f"Sending email to {self.settings['notification_email']}")
        msg = MIMEText(message)
        msg['Subject'] = subject
        msg['From'] = self.settings['smtp_username']
        msg['To'] = self.settings['notification_email']

        with smtplib.SMTP(self.settings['smtp_server'], self.settings['smtp_port']) as server:
            server.starttls()
            server.login(self.settings['smtp_username'], self.settings['smtp_password'])
            server.send_message(msg)

    def test_notification_settings(self):
        """Test notification settings and return detailed status."""
        status = {
            'telegram': {'enabled': False, 'configured': False, 'error': None},
            'email': {'enabled': False, 'configured': False, 'error': None}
        }
        
        if not self.settings:
            return {'error': 'No settings found in database'}
            
        # Check Telegram settings
        status['telegram']['enabled'] = self.settings.get('enable_telegram_notifications', False)
        if status['telegram']['enabled']:
            if self.settings.get('telegram_bot_token') and self.settings.get('telegram_chat_id'):
                status['telegram']['configured'] = True
            else:
                status['telegram']['error'] = 'Missing bot token or chat ID'
                
        # Check Email settings
        status['email']['enabled'] = self.settings.get('enable_email_notifications', False)
        if status['email']['enabled']:
            required = ['smtp_server', 'smtp_port', 'smtp_username', 
                       'smtp_password', 'notification_email']
            missing = [s for s in required if not self.settings.get(s)]
            if not missing:
                status['email']['configured'] = True
            else:
                status['email']['error'] = f'Missing settings: {", ".join(missing)}'
                
        return status