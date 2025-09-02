"""Database connection and ORM setup."""

import os
from flask_sqlalchemy import SQLAlchemy
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
    return psycopg2.connect(**DB_CONFIG)

class Database:
    @staticmethod
    def get_connection():
        """Get a database connection using environment variables."""
        return get_db_connection()

    @staticmethod
    def execute_query(query, params=None, fetch=True):
        """Execute a query and optionally fetch results
        
        Args:
            query (str): The SQL query to execute
            params (tuple, optional): Query parameters. Defaults to None.
            fetch (bool, optional): Whether to fetch results. Defaults to True.
        
        Returns:
            list: Query results if fetch=True, otherwise None
        """
        conn = Database.get_connection()
        cur = conn.cursor()
        try:
            cur.execute(query, params)
            if fetch:
                result = cur.fetchall()
            else:
                result = None
                if cur.statusmessage.startswith('DELETE') or cur.statusmessage.startswith('UPDATE'):
                    result = cur.rowcount
            conn.commit()
            return result
        finally:
            cur.close()
            conn.close()

    @staticmethod
    def execute_query_single(query, params=None):
        """Execute a query and fetch a single row
        
        Args:
            query (str): The SQL query to execute
            params (tuple, optional): Query parameters. Defaults to None.
        
        Returns:
            tuple: A single row result or None if no results
        """
        conn = Database.get_connection()
        cur = conn.cursor()
        try:
            cur.execute(query, params)
            result = cur.fetchone()
            conn.commit()
            return result
        finally:
            cur.close()
            conn.close()

    @staticmethod
    def execute_transaction(queries):
        """Execute multiple queries in a transaction"""
        conn = Database.get_connection()
        cur = conn.cursor()
        try:
            for query, params in queries:
                cur.execute(query, params)
            conn.commit()
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            cur.close()
            conn.close()
