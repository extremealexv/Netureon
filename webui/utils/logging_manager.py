import logging
from flask import current_app
from ..models.database import Database
import sys
import os

# Add the project root to Python path to import netureon modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

try:
    from netureon.config.logging_config import get_logging_level_from_db, reconfigure_existing_loggers
except ImportError:
    # Fallback if the centralized logging module is not available
    def get_logging_level_from_db():
        return logging.INFO
    def reconfigure_existing_loggers():
        return True

def configure_logging(app=None):
    """Configure logging levels for all modules based on database settings"""
    try:
        # Try to use the centralized logging configuration first
        if reconfigure_existing_loggers():
            logging.getLogger('webui').info("Logging reconfigured using centralized system")
            return True
        
        # Fallback to original method if centralized approach fails
        # If app is provided, use its context
        if app:
            ctx = app.app_context()
        else:
            # Try to get current app context
            try:
                ctx = current_app.app_context()
            except RuntimeError:
                # Set default logging if no app context
                logging.getLogger().setLevel(logging.INFO)
                return True

        with ctx:
            # Get logging level from configuration
            result = Database.execute_query("""
                SELECT value 
                FROM configuration 
                WHERE key = 'logging_level'
            """)
            
            level = 'INFO'  # Default level
            if result and result[0]:
                configured_level = result[0]['value'].upper()
                if hasattr(logging, configured_level):
                    level = configured_level

            # Configure root logger
            root_logger = logging.getLogger()
            root_logger.setLevel(getattr(logging, level))

            # Configure module loggers
            modules = [
                'webui',
                'webui.routes',
                'webui.models',
                'webui.alerts',
                'webui.handlers',
                'webui.utils',
                'netureon'  # Add the main netureon logger
            ]

            for module in modules:
                logger = logging.getLogger(module)
                logger.setLevel(getattr(logging, level))
                # Also update handlers if they exist
                for handler in logger.handlers:
                    handler.setLevel(getattr(logging, level))

            logging.getLogger('webui').info(f"Logging level set to {level}")
            return True

    except Exception as e:
        logging.getLogger('webui').error(f"Failed to configure logging: {str(e)}")
        return False