from .base import BaseNotifier
import requests

class TelegramNotifier(BaseNotifier):
    def __init__(self):
        super().__init__()
        self.bot_token = self.settings.get('telegram_bot_token')
        self.chat_id = self.settings.get('telegram_chat_id')

    def send_notification(self, message):
        """Send message via Telegram."""
        if not self.bot_token or not self.chat_id:
            self.logger.warning("Telegram not configured - skipping notification")
            return False

        try:
            url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"
            data = {
                "chat_id": self.chat_id,
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