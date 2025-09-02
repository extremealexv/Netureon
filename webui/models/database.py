"""Database connection and ORM setup."""

import os
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import text
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Create the SQLAlchemy instance
db = SQLAlchemy()

def init_db(app):
    """Initialize the database with the Flask app."""
    # Configure SQLAlchemy
    app.config['SQLALCHEMY_DATABASE_URI'] = (
        f"postgresql://{os.getenv('DB_USER')}:{os.getenv('DB_PASSWORD')}@"
        f"{os.getenv('DB_HOST')}:{os.getenv('DB_PORT')}/{os.getenv('DB_NAME')}"
    )
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    
    # Initialize SQLAlchemy with the app
    db.init_app(app)

    # Create all tables
    with app.app_context():
        db.create_all()

class Database:
    _flask_app = None

    @classmethod
    def _get_app(cls):
        """Get or create Flask app instance."""
        if cls._flask_app is None:
            # Import here to avoid circular imports
            from webui.app import app
            cls._flask_app = app
        return cls._flask_app

    @classmethod
    def execute_query(cls, query, params=None, fetch=True):
        """Execute a query and optionally fetch results using SQLAlchemy
        
        Args:
            query (str): The SQL query to execute
            params (dict, optional): Query parameters. Defaults to None.
            fetch (bool, optional): Whether to fetch results. Defaults to True.
        
        Returns:
            list: Query results if fetch=True, otherwise None
        """
        app = cls._get_app()
        with app.app_context():
            if params is None:
                params = {}
            result = db.session.execute(text(query), params)
            if fetch:
                return result.fetchall()
            db.session.commit()
            return result.rowcount if result.rowcount > -1 else None

    @classmethod
    def execute_query_single(cls, query, params=None):
        """Execute a query and fetch a single row using SQLAlchemy
        
        Args:
            query (str): The SQL query to execute
            params (dict, optional): Query parameters. Defaults to None.
        
        Returns:
            tuple: A single row result or None if no results
        """
        app = cls._get_app()
        with app.app_context():
            if params is None:
                params = {}
            result = db.session.execute(text(query), params)
            return result.fetchone()

    @classmethod
    def execute_transaction(cls, queries):
        """Execute multiple queries in a transaction using SQLAlchemy"""
        app = cls._get_app()
        with app.app_context():
            try:
                for query, params in queries:
                    if params is None:
                        params = {}
                    db.session.execute(text(query), params)
                db.session.commit()
            except Exception as e:
                db.session.rollback()
                raise e
