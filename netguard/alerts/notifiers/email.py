from .base import BaseNotifier
import smtplib
from email.mime.text import MIMEText

class EmailNotifier(BaseNotifier):
    def __init__(self):
        super().__init__()
        self.settings = self.get_notification_settings()
        
    def is_configured(self):
        if self.settings['enable_email_notifications'] != 'true':
            self.logger.info("Email notifications are disabled")
            return False
            
        required = ['smtp_server', 'smtp_port', 'smtp_username', 
                   'smtp_password', 'smtp_from_address', 'smtp_to_address']
        
        missing = [s for s in required if not self.settings.get(s)]
        if missing:
            self.logger.error(f"Email configuration incomplete. Missing: {', '.join(missing)}")
            return False
            
        return True

    def send_notification(self, subject, body):
        if not self.is_configured():
            return False
            
        try:
            server = smtplib.SMTP(self.settings['smtp_server'], 
                                int(self.settings['smtp_port']))
            server.starttls()
            server.login(self.settings['smtp_username'], 
                        self.settings['smtp_password'])
            
            message = MIMEText(body)
            message['Subject'] = subject
            message['From'] = self.settings['smtp_from_address']
            message['To'] = self.settings['smtp_to_address']
            
            server.send_message(message)
            server.quit()
            
            self.logger.info("Email sent successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to send email: {str(e)}")
            return False