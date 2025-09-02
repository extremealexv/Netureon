"""WebUI package initialization."""

from flask import Flask
from .config.config import Config

def create_app():
    app = Flask(__name__)
    app.secret_key = Config.SECRET_KEY
    
    # Initialize database first
    from .models.database import db, init_db
    init_db(app)

    # Push an application context
    app.app_context().push()
    
    # Import models to ensure they're registered with SQLAlchemy
    from .models.config import Configuration
    
    # Create all database tables
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
