"""Database connection and ORM setup."""

import os
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

class Database:
    @staticmethod
    def execute_query(query, params=None, fetch=True):
        """Execute a query and optionally fetch results using SQLAlchemy
        
        Args:
            query (str): The SQL query to execute
            params (dict, optional): Query parameters. Defaults to None.
            fetch (bool, optional): Whether to fetch results. Defaults to True.
        
        Returns:
            list: Query results if fetch=True, otherwise None
        """
        with db.engine.connect() as conn:
            if params is None:
                params = {}
            result = conn.execute(text(query), params)
            if fetch:
                return result.fetchall()
            return result.rowcount if result.rowcount > -1 else None

    @staticmethod
    def execute_query_single(query, params=None):
        """Execute a query and fetch a single row using SQLAlchemy
        
        Args:
            query (str): The SQL query to execute
            params (dict, optional): Query parameters. Defaults to None.
        
        Returns:
            tuple: A single row result or None if no results
        """
        with db.engine.connect() as conn:
            if params is None:
                params = {}
            result = conn.execute(text(query), params)
            return result.fetchone()

    @staticmethod
    def execute_transaction(queries):
        """Execute multiple queries in a transaction using SQLAlchemy"""
        with db.engine.begin() as conn:
            try:
                for query, params in queries:
                    if params is None:
                        params = {}
                    conn.execute(text(query), params)
            except Exception as e:
                raise e
