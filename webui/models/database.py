"""Database connection and ORM setup."""

import os
from flask import Flask, current_app
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
    """Database access class with SQLAlchemy integration."""
    
    def __init__(self):
        """Initialize Database instance."""
        self._flask_app = None

    def _ensure_app_context(self):
        """Ensure we have a valid Flask application context."""
        try:
            # Try to get the current app context
            current_app._get_current_object()
        except RuntimeError:
            # If no app context exists, create a temporary one
            if not self._flask_app:
                self._flask_app = Flask('netguard_temp')
                self._flask_app.config['SQLALCHEMY_DATABASE_URI'] = (
                    f"postgresql://{os.getenv('DB_USER')}:{os.getenv('DB_PASSWORD')}@"
                    f"{os.getenv('DB_HOST')}:{os.getenv('DB_PORT')}/{os.getenv('DB_NAME')}"
                )
                self._flask_app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
                db.init_app(self._flask_app)
            return self._flask_app.app_context()
        return None

    def execute_query(self, query, params=None, fetch=True):
        """Execute a query and optionally fetch results using SQLAlchemy
        
        Args:
            query (str): The SQL query to execute
            params (dict, optional): Query parameters. Defaults to None.
            fetch (bool, optional): Whether to fetch results. Defaults to True.
        
        Returns:
            list: Query results if fetch=True, otherwise None
        """
        ctx = self._ensure_app_context()
        if ctx:
            ctx.push()
            
        try:
            if params is None:
                params = {}
            result = db.session.execute(text(query), params)
            if fetch:
                return result.fetchall()
            db.session.commit()
            return result.rowcount if result.rowcount > -1 else None
        finally:
            if ctx:
                ctx.pop()

    def execute_query_single(self, query, params=None):
        """Execute a query and fetch a single row using SQLAlchemy
        
        Args:
            query (str): The SQL query to execute
            params (dict, optional): Query parameters. Defaults to None.
        
        Returns:
            tuple: A single row result or None if no results
        """
        ctx = self._ensure_app_context()
        if ctx:
            ctx.push()
            
        try:
            if params is None:
                params = {}
            result = db.session.execute(text(query), params)
            return result.fetchone()
        finally:
            if ctx:
                ctx.pop()

    def execute_transaction(self, queries):
        """Execute multiple queries in a transaction using SQLAlchemy"""
        ctx = self._ensure_app_context()
        if ctx:
            ctx.push()
            
        try:
            for query, params in queries:
                if params is None:
                    params = {}
                db.session.execute(text(query), params)
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            raise e
        finally:
            if ctx:
                ctx.pop()
                
    # Static method shortcuts for convenience
    @staticmethod
    def query(*args, **kwargs):
        """Static shortcut for execute_query"""
        return Database().execute_query(*args, **kwargs)
        
    @staticmethod
    def query_single(*args, **kwargs):
        """Static shortcut for execute_query_single"""
        return Database().execute_query_single(*args, **kwargs)
        
    @staticmethod
    def transaction(*args, **kwargs):
        """Static shortcut for execute_transaction"""
        return Database().execute_transaction(*args, **kwargs)
