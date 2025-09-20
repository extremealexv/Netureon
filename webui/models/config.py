"""Configuration model for Netureon."""
from datetime import datetime
from .database import db, Database
import logging

class Configuration(db.Model):
    """Configuration model for storing application settings."""
    __tablename__ = 'configuration'

    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(50), unique=True, nullable=False)
    value = db.Column(db.String(500))
    updated_at = db.Column(db.DateTime, default=datetime.utcnow)

    @staticmethod
    def get_setting(key, default=None):
        """Get a configuration setting by key."""
        setting = Configuration.query.filter_by(key=key).first()
        return setting.value if setting else default

    @staticmethod
    def set_setting(key, value):
        """Set a configuration setting."""
        setting = Configuration.query.filter_by(key=key).first()
        if setting:
            setting.value = value
            setting.updated_at = datetime.utcnow()
        else:
            setting = Configuration(key=key, value=value)
            db.session.add(setting)
        db.session.commit()

    @staticmethod
    def get_all_settings():
        """Get all configuration settings as a dictionary."""
        settings = Configuration.query.all()
        return {s.key: s.value for s in settings}

class Config:
    @staticmethod
    def get_email_config():
        """Get email configuration using Configuration model"""
        try:
            return {
                'smtp_server': Configuration.get_setting('smtp_server'),
                'smtp_port': int(Configuration.get_setting('smtp_port', '587')),
                'smtp_user': Configuration.get_setting('smtp_user'),
                'smtp_password': Configuration.get_setting('smtp_password'),
                'email_from': Configuration.get_setting('email_from'),
                'email_to': Configuration.get_setting('email_to')
            }
        except Exception as e:
            logging.error(f"Failed to get email config: {str(e)}")
            return None

    @staticmethod
    def get_telegram_config():
        """Get telegram configuration using Configuration model"""
        try:
            bot_token = Configuration.get_setting('telegram_bot_token')
            chat_id = Configuration.get_setting('telegram_chat_id')
            
            if bot_token and chat_id:
                return {
                    'bot_token': bot_token,
                    'chat_id': chat_id
                }
            return None
        except Exception as e:
            logging.error(f"Failed to get telegram config: {str(e)}")
            return None
