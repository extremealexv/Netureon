"""WebUI package initialization."""

import os
from dotenv import load_dotenv
from flask import Flask
from .config.config import Config

# Load environment variables
load_dotenv()

def create_app():
    app = Flask(__name__)
    app.secret_key = Config.SECRET_KEY
    
    # Configure SQLAlchemy
    app.config['SQLALCHEMY_DATABASE_URI'] = (
        f"postgresql://{os.getenv('DB_USER')}:{os.getenv('DB_PASSWORD')}@"
        f"{os.getenv('DB_HOST')}:{os.getenv('DB_PORT')}/{os.getenv('DB_NAME')}"
    )
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    
    # Initialize database
    from .models.database import db
    db.init_app(app)
    
    # Register blueprints and initialize routes
    with app.app_context():
        from .routes.review import review
        from .routes.main import main
        from .routes.config import config
        from .routes.unknown import unknown
        from .routes.system import system
        
        app.register_blueprint(main)
        app.register_blueprint(review)
        app.register_blueprint(config)
        app.register_blueprint(unknown)
        app.register_blueprint(system)
    
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
