from ..logging.logger import setup_logging
import os
from dotenv import load_dotenv

load_dotenv()

class Settings:
    _instance = None
    _settings_cache = {}
    logger = setup_logging('netureon.settings')
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(Settings, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if not self._initialized:
            self._initialized = True
            self._settings_cache = {}
            
    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = Settings()
        return cls._instance

    def get_db_config(self):
        """Get database configuration settings."""
        return {
            'dbname': os.getenv('DB_NAME', 'netureon'),
            'user': os.getenv('DB_USER', 'netureon'),
            'password': os.getenv('DB_PASSWORD', ''),
            'host': os.getenv('DB_HOST', 'localhost'),
            'port': os.getenv('DB_PORT', '5432')
        }
    
    def get_setting(self, key, default=None):
        """Get setting from cache or environment."""
        if key in self._settings_cache:
            return self._settings_cache[key]
            
        env_value = os.getenv(key.upper())
        if env_value is not None:
            self._settings_cache[key] = env_value
            return env_value
            
        return default
            
    def get_notification_settings(self):
        """Get all notification related settings."""
        settings = {
            'enable_email_notifications': self.get_setting('enable_email_notifications', 'false'),
            'enable_telegram_notifications': self.get_setting('enable_telegram_notifications', 'false'),
            'smtp_server': self.get_setting('smtp_server'),
            'smtp_port': self.get_setting('smtp_port', '587'),
            'smtp_username': self.get_setting('smtp_username'),
            'smtp_password': self.get_setting('smtp_password'),
            'smtp_from_address': self.get_setting('smtp_from_address'),
            'smtp_to_address': self.get_setting('smtp_to_address'),
            'telegram_bot_token': self.get_setting('telegram_bot_token'),
            'telegram_chat_id': self.get_setting('telegram_chat_id')
        }
        
        # Convert string boolean values
        for key in ['enable_email_notifications', 'enable_telegram_notifications']:
            if isinstance(settings[key], str):
                settings[key] = settings[key].lower() == 'true'
                
        return settings