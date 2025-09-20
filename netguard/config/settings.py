NetGuard\netguard\config\settings.py
import os
from dotenv import load_dotenv
from webui.models.config import Configuration

load_dotenv()

class Settings:
    @staticmethod
    def get_db_config():
        return {
            'dbname': os.getenv('DB_NAME'),
            'user': os.getenv('DB_USER'),
            'password': os.getenv('DB_PASSWORD'),
            'host': os.getenv('DB_HOST'),
            'port': os.getenv('DB_PORT')
        }

    @staticmethod
    def get_notification_settings():
        """Get notification settings from the database."""
        return {
            'enable_email_notifications': Configuration.get_setting('enable_email_notifications'),
            'enable_telegram_notifications': Configuration.get_setting('enable_telegram_notifications'),
            'smtp_server': Configuration.get_setting('smtp_server'),
            'smtp_port': Configuration.get_setting('smtp_port', '587'),
            'smtp_username': Configuration.get_setting('smtp_username'),
            'smtp_password': Configuration.get_setting('smtp_password'),
            'smtp_from_address': Configuration.get_setting('smtp_from_address'),
            'smtp_to_address': Configuration.get_setting('smtp_to_address'),
            'telegram_bot_token': Configuration.get_setting('telegram_bot_token'),
            'telegram_chat_id': Configuration.get_setting('telegram_chat_id')
        }