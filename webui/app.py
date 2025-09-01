from flask import Flask
from config.config import Config
from routes.main import main
from routes.review import review
from routes.unknown import unknown
from routes.system import bp as system_bp

def create_app():
    app = Flask(__name__)
    app.secret_key = Config.SECRET_KEY
    
    # Register blueprints
    app.register_blueprint(main)
    app.register_blueprint(review)
    app.register_blueprint(unknown)
    app.register_blueprint(system_bp)
    
    return app

if __name__ == '__main__':
    app = create_app()
    app.run(host='0.0.0.0', port=5000)
