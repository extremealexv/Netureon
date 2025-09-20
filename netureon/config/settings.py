import os
from dotenv import load_dotenv
import psycopg2
from ..logging.logger import setup_logging

logger = setup_logging('netureon.settings')

class Settings:
    _instance = None
    _settings_cache = {}
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(Settings, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if not self._initialized:
            self._initialized = True
            self._settings_cache = {}
            load_dotenv()
            self._db_params = {
                'dbname': os.getenv('DB_NAME'),
                'user': os.getenv('DB_USER'),
                'password': os.getenv('DB_PASSWORD'),
                'host': os.getenv('DB_HOST'),
                'port': os.getenv('DB_PORT')
            }
            logger.info("Settings initialized with database connection from .env")

    @classmethod
    def get_instance(cls):
        """Get singleton instance of Settings."""
        if cls._instance is None:
            cls._instance = Settings()
        return cls._instance
    
    def get_db_config(self):
        """Get database configuration from .env file."""
        return self._db_params

    def get_setting(self, key, default=None):
        """Get setting from database configuration table."""
        if key in self._settings_cache:
            return self._settings_cache[key]
            
        try:
            with psycopg2.connect(**self._db_params) as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        "SELECT value FROM configuration WHERE key = %s",
                        (key,)
                    )
                    result = cur.fetchone()
                    
                    if result:
                        value = result[0]
                        self._settings_cache[key] = value
                        return value
                    
                    logger.debug(f"Setting {key} not found in database")
                    return default
                    
        except Exception as e:
            logger.error(f"Error fetching setting {key} from database: {e}")
            return default

    def get_notification_settings(self):
        """Get notification settings from database configuration table."""
        settings = {
            'enable_email_notifications': self.get_setting('enable_email_notifications', 'false'),
            'enable_telegram_notifications': self.get_setting('enable_telegram_notifications', 'false'),
            'smtp_server': self.get_setting('smtp_server'),
            'smtp_port': self.get_setting('smtp_port'),
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

    def refresh(self):
        """Clear settings cache to force reload from database."""
        self._settings_cache.clear()
        logger.debug("Settings cache cleared")