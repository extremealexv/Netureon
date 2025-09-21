"""WebUI package initialization."""

import os
from dotenv import load_dotenv
from flask import Flask
from .config.config import Config
from .models.database import db
from .utils.logging_manager import configure_logging

# Load environment variables
load_dotenv()

def create_app():
    """Create and configure the Flask application."""
    app = Flask(__name__)
    
    # Configure logging with app context
    configure_logging(app)
    
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
    
    @app.before_request
    def before_request():
        # Reconfigure logging on each request to pick up changes
        configure_logging(app)
    
    return app
