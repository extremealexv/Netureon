import os
import logging
from logging.handlers import RotatingFileHandler

def setup_logging(name='netureon'):
    """Configure logging with rotation."""
    log_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '../../logs')
    os.makedirs(log_dir, exist_ok=True)
    
    log_file = os.path.join(log_dir, f'{name}.log')
    
    handler = RotatingFileHandler(
        log_file,
        maxBytes=10*1024*1024,
        backupCount=5,
        delay=False,
        mode='a'
    )
    
    formatter = logging.Formatter(
        '%(asctime)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    handler.setFormatter(formatter)
    
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)
    logger.handlers = []
    logger.addHandler(handler)
    
    return logger