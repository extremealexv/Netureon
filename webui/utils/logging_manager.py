import logging
from ..models.database import Database

def configure_logging():
    """Configure logging levels for all modules based on database settings"""
    try:
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
            'webui.utils'
        ]

        for module in modules:
            logger = logging.getLogger(module)
            logger.setLevel(getattr(logging, level))

        logging.getLogger('webui').info(f"Logging level set to {level}")
        return True

    except Exception as e:
        logging.getLogger('webui').error(f"Failed to configure logging: {str(e)}")
        return False