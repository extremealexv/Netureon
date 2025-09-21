import logging
from ..models.database import Database

class Notifier:
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        
    def send_notification(self, subject, message, notification_type="info"):
        """Send notification via configured channels."""
        try:
            # Get notification settings from database
            settings = Database.execute_query("""
                SELECT enable_telegram_notifications, 
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
            
            if not settings:
                self.logger.error("No notification settings found")
                return False
                
            settings = settings[0]
            success = False
            
            # Send Telegram notification if enabled
            if settings['enable_telegram_notifications']:
                from telegram import Bot
                bot = Bot(token=settings['telegram_bot_token'])
                bot.send_message(
                    chat_id=settings['telegram_chat_id'],
                    text=f"{subject}\n\n{message}"
                )
                success = True
                self.logger.info("Telegram notification sent")
                
            # Send email notification if enabled
            if settings['enable_email_notifications']:
                import smtplib
                from email.mime.text import MIMEText
                
                msg = MIMEText(message)
                msg['Subject'] = subject
                msg['From'] = settings['smtp_username']
                msg['To'] = settings['notification_email']
                
                with smtplib.SMTP(settings['smtp_server'], settings['smtp_port']) as server:
                    server.starttls()
                    server.login(settings['smtp_username'], settings['smtp_password'])
                    server.send_message(msg)
                    
                success = True
                self.logger.info("Email notification sent")
                
            return success
            
        except Exception as e:
            self.logger.error(f"Failed to send notification: {str(e)}")
            return False