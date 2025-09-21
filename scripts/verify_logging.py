import logging
import sys
sys.path.append('.')

from webui.utils.logging_manager import configure_logging
from webui.models.database import Database

def verify_logging():
    """Verify logging configuration across all modules"""
    # Configure logging
    if not configure_logging():
        print("Failed to configure logging")
        return False
        
    # Test logging for each module
    modules = {
        'webui': logging.getLogger('webui'),
        'routes': logging.getLogger('webui.routes'),
        'models': logging.getLogger('webui.models'),
        'alerts': logging.getLogger('webui.alerts'),
        'handlers': logging.getLogger('webui.handlers'),
        'utils': logging.getLogger('webui.utils')
    }
    
    print("\nTesting logging levels for each module:")
    for name, logger in modules.items():
        print(f"\nModule: {name}")
        print(f"Level: {logging.getLevelName(logger.getEffectiveLevel())}")
        
        # Test all logging levels
        logger.debug(f"Debug message from {name}")
        logger.info(f"Info message from {name}")
        logger.warning(f"Warning message from {name}")
        logger.error(f"Error message from {name}")
        
    return True

if __name__ == "__main__":
    verify_logging()