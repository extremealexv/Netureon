from abc import ABC, abstractmethod
from ...logging.logger import setup_logging
from ...config.settings import Settings

class BaseNotifier(ABC):
    def __init__(self):
        self.logger = setup_logging('netureon.notifier')
        self._settings = None
    
    @property
    def settings(self):
        """Get fresh settings each time to catch updates."""
        if not self._settings:
            self._settings = Settings.get_instance().get_notification_settings()
        return self._settings
    
    def refresh_settings(self):
        """Force settings refresh."""
        self._settings = None
        return self.settings

    @abstractmethod
    def is_configured(self):
        """Check if the notifier is properly configured."""
        pass

    @abstractmethod
    def send_notification(self, message):
        """Send notification using the specific channel."""
        pass