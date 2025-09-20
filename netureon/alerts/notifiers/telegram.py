from .base import BaseNotifier
import requests

class TelegramNotifier(BaseNotifier):
    def is_configured(self):
        """Check if Telegram notifications are properly configured."""
        settings = self.refresh_settings()  # Get fresh settings
        
        if not settings['enable_telegram_notifications']:
            self.logger.info("Telegram notifications are disabled in settings")
            return False
            
        if not settings['telegram_bot_token'] or not settings['telegram_chat_id']:
            self.logger.warning("Telegram configuration incomplete - missing bot_token or chat_id")
            return False
            
        return True

    def send_notification(self, message):
        """Send message via Telegram."""
        if not self.is_configured():
            return False

        try:
            url = f"https://api.telegram.org/bot{self.settings['telegram_bot_token']}/sendMessage"
            data = {
                "chat_id": self.settings['telegram_chat_id'],
                "text": message,
                "parse_mode": "HTML"
            }
            
            response = requests.post(url, data=data, timeout=10)
            response.raise_for_status()
            
            self.logger.info("Telegram notification sent successfully")
            return True
                
        except Exception as e:
            self.logger.error(f"Failed to send Telegram notification: {str(e)}")
            return False