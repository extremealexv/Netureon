"""WebUI package initialization."""

import os
from dotenv import load_dotenv
from flask import Flask
from .config.config import Config
from .models.database import db
import logging

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('netureon.log'),
        logging.StreamHandler()
    ]
)

def create_app():
    app = Flask(__name__)
    app.secret_key = Config.SECRET_KEY
    
    # Configure SQLAlchemy
    app.config['SQLALCHEMY_DATABASE_URI'] = (
        f"postgresql://{os.getenv('DB_USER')}:{os.getenv('DB_PASSWORD')}@"
        f"{os.getenv('DB_HOST')}:{os.getenv('DB_PORT')}/{os.getenv('DB_NAME')}"
    )
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    
    # Initialize extensions
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
