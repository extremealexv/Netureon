import os
from dotenv import load_dotenv

load_dotenv()

class Settings:
    def __init__(self):
        self._settings_cache = {}

    def get_setting(self, key, default=None):
        """Get setting with proper boolean conversion."""
        if key in self._settings_cache:
            return self._settings_cache[key]

        try:
            from webui.models.config import Configuration
            value = Configuration.get_setting(key, default)
            
            # Convert string boolean values to actual booleans
            if isinstance(value, str):
                if value.lower() == 'true':
                    value = True
                elif value.lower() == 'false':
                    value = False
                    
            self._settings_cache[key] = value
            return value
            
        except Exception as e:
            self.logger.error(f"Error getting setting {key}: {e}")
            return default

    def get_notification_settings(self):
        """Get notification settings with proper boolean flags."""
        return {
            'enable_email_notifications': self.get_setting('enable_email_notifications', False),
            'enable_telegram_notifications': self.get_setting('enable_telegram_notifications', False),
            'smtp_server': self.get_setting('smtp_server'),
            'smtp_port': self.get_setting('smtp_port', '587'),
            'smtp_username': self.get_setting('smtp_username'),
            'smtp_password': self.get_setting('smtp_password'),
            'smtp_from_address': self.get_setting('smtp_from_address'),
            'smtp_to_address': self.get_setting('smtp_to_address'),
            'telegram_bot_token': self.get_setting('telegram_bot_token'),
            'telegram_chat_id': self.get_setting('telegram_chat_id')
        }