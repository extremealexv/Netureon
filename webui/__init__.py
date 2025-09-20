"""WebUI package initialization."""

import os
from dotenv import load_dotenv
from flask import Flask
from .config.config import Config
from .models.database import db
import logging
from logging.handlers import RotatingFileHandler

# Load environment variables
load_dotenv()

# Configure logging
log_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
log_file = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'logs', 'netureon.log')

# Create logs directory if it doesn't exist
os.makedirs(os.path.dirname(log_file), exist_ok=True)

# Setup file handler with rotation
file_handler = RotatingFileHandler(log_file, maxBytes=10485760, backupCount=5)
file_handler.setFormatter(log_formatter)
file_handler.setLevel(logging.DEBUG)

# Setup console handler
console_handler = logging.StreamHandler()
console_handler.setFormatter(log_formatter)
console_handler.setLevel(logging.INFO)

# Configure root logger
root_logger = logging.getLogger()
root_logger.setLevel(logging.DEBUG)
root_logger.addHandler(file_handler)
root_logger.addHandler(console_handler)

def create_app():
    """Create and configure the Flask application."""
    app = Flask(__name__)
    
    # Load configuration
    app.config.from_object('webui.config.config.Config')
    
    # Initialize database
    db.init_app(app)
    
    # Register blueprints and initialize routes
    with app.app_context():
        # Import blueprints
        from .routes.review import review
        from .routes.main import main
        from .routes.config import config_bp
        from .routes.unknown import unknown
        from .routes.system import bp as system_bp
        
        # Register blueprints
        app.register_blueprint(main)
        app.register_blueprint(review)
        app.register_blueprint(config_bp)
        app.register_blueprint(unknown)
        app.register_blueprint(system_bp)
        
        return app
    
    # Import all models to ensure they're registered with SQLAlchemy
    from .models.config import Configuration
    
    # Create/update all tables
    with app.app_context():
        db.create_all()
    
    # Import and register blueprints
    from .routes.main import main
    from .routes.review import review
    from .routes.unknown import unknown
    from .routes.system import bp as system_bp
    from .routes.config import config_bp
    
    app.register_blueprint(main)
    app.register_blueprint(review)
    app.register_blueprint(unknown)
    app.register_blueprint(system_bp)
    app.register_blueprint(config_bp)
    
    return app
