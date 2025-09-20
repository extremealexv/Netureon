from abc import ABC, abstractmethod
from ...logging.logger import setup_logging

class BaseNotifier(ABC):
    def __init__(self):
        self.logger = setup_logging('netureon.notifier')
        self.settings = None
    
    @abstractmethod
    def send_notification(self, subject, body):
        """Send notification using the specific channel."""
        pass

    @abstractmethod
    def is_configured(self):
        """Check if the notifier is properly configured."""
        pass