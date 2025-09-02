"""Configuration model for NetGuard."""
from datetime import datetime
from .database import db

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
