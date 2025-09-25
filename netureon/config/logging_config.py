"""
Centralized logging configuration for Netureon.
This module provides logging configuration that can be used across all components.
"""

import logging
import os
import psycopg2
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def get_logging_level_from_db():
    """Get the logging level from the configuration database."""
    try:
        # Database configuration
        db_config = {
            'dbname': os.getenv('DB_NAME', 'netguard'),
            'user': os.getenv('DB_USER', 'postgres'),
            'password': os.getenv('DB_PASSWORD'),
            'host': os.getenv('DB_HOST', 'localhost'),
            'port': os.getenv('DB_PORT', '5432')
        }
        
        with psycopg2.connect(**db_config) as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT value 
                    FROM configuration 
                    WHERE key = 'logging_level'
                """)
                result = cur.fetchone()
                
                if result and result[0]:
                    level_name = result[0].upper()
                    if hasattr(logging, level_name):
                        return getattr(logging, level_name)
                
                # Default to INFO if not found or invalid
                return logging.INFO
                
    except Exception as e:
        # If database is not available or any error occurs, default to INFO
        print(f"Warning: Could not read logging level from database: {e}")
        return logging.INFO

def configure_logger(logger_name, log_file_path=None, console_level=None, file_level=None):
    """Configure a logger with both console and file handlers using database settings."""
    
    # Get logging level from database
    db_level = get_logging_level_from_db()
    
    # Use database level if specific levels not provided
    if console_level is None:
        console_level = db_level
    if file_level is None:
        file_level = db_level
    
    logger = logging.getLogger(logger_name)
    logger.setLevel(min(console_level, file_level))  # Set to the most verbose level
    
    # Remove existing handlers
    logger.handlers = []
    
    # Create formatter
    formatter = logging.Formatter(
        '%(asctime)s - %(levelname)s - %(name)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(console_level)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    # File handler (if path provided)
    if log_file_path:
        from logging.handlers import RotatingFileHandler
        
        # Ensure log directory exists
        os.makedirs(os.path.dirname(log_file_path), exist_ok=True)
        
        file_handler = RotatingFileHandler(
            log_file_path,
            maxBytes=10*1024*1024,  # 10MB
            backupCount=5,
            delay=False,
            mode='a+'
        )
        file_handler.setLevel(file_level)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    
    return logger

def reconfigure_existing_loggers():
    """Reconfigure all existing loggers to use the current database logging level."""
    try:
        db_level = get_logging_level_from_db()
        
        # Get all existing loggers
        existing_loggers = [logging.getLogger(name) for name in logging.Logger.manager.loggerDict]
        
        # Update root logger
        root_logger = logging.getLogger()
        root_logger.setLevel(db_level)
        
        # Update all handlers of root logger
        for handler in root_logger.handlers:
            handler.setLevel(db_level)
        
        # Update existing loggers
        for logger in existing_loggers:
            if logger.handlers:  # Only update loggers that have handlers
                logger.setLevel(db_level)
                for handler in logger.handlers:
                    handler.setLevel(db_level)
        
        print(f"Reconfigured loggers to level: {logging.getLevelName(db_level)}")
        return True
        
    except Exception as e:
        print(f"Failed to reconfigure loggers: {e}")
        return False