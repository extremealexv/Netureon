from .base import BaseNotifier
import smtplib
from email.mime.text import MIMEText

class EmailNotifier(BaseNotifier):
    def __init__(self):
        super().__init__()

    def is_configured(self):
        """Check if email notifications are properly configured."""
        if not self.settings.get('enable_email_notifications'):
            self.logger.info("Email notifications are disabled")
            return False

        required_settings = [
            'smtp_server',
            'smtp_port',
            'smtp_username',
            'smtp_password',
            'smtp_from_address',
            'smtp_to_address'
        ]

        missing = [s for s in required_settings if not self.settings.get(s)]
        if missing:
            self.logger.error(f"Email configuration incomplete. Missing: {', '.join(missing)}")
            return False

        return True

    def send_notification(self, subject, message):
        """Send email notification."""
        if not self.is_configured():
            return False

        try:
            msg = MIMEText(message)
            msg['Subject'] = subject
            msg['From'] = self.settings['smtp_from_address']
            msg['To'] = self.settings['smtp_to_address']

            server = smtplib.SMTP(self.settings['smtp_server'], 
                                int(self.settings['smtp_port']))
            server.starttls()
            server.login(self.settings['smtp_username'], 
                        self.settings['smtp_password'])
            server.send_message(msg)
            server.quit()
            
            self.logger.info("Email sent successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to send email: {str(e)}")
            return False