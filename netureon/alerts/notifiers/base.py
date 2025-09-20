from abc import ABC, abstractmethod
from ...logging.logger import setup_logging
from ...config.settings import Settings

class BaseNotifier(ABC):
    def __init__(self):
        self.logger = setup_logging('netureon.notifier')
        self.settings = Settings.get_notification_settings()
    
    @abstractmethod
    def send_notification(self, message):
        """Send notification using the specific channel."""
        pass

    @abstractmethod
    def is_configured(self):
        """Check if the notifier is properly configured."""
        pass