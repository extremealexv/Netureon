"""WebUI package initialization."""

from flask import Flask
from .config.config import Config

def create_app():
    app = Flask(__name__)
    app.secret_key = Config.SECRET_KEY
    
    # Initialize database
    from .models.database import db, init_db
    init_db(app)
    
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
