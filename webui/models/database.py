"""Database connection and ORM setup."""

from flask import Flask, current_app
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import text

# Create the SQLAlchemy instance
db = SQLAlchemy()

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

    def _execute_query_impl(self, query, params=None, fetch=True):
        """Internal implementation of execute_query
        
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

    def _execute_query_single_impl(self, query, params=None):
        """Internal implementation of execute_query_single
        
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

    def _execute_transaction_impl(self, queries):
        """Internal implementation of execute_transaction"""
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
                
    # Static method public interface
    @staticmethod
    def execute_query(query, params=None, fetch=True):
        """Execute a query and optionally fetch results
        
        Args:
            query (str): The SQL query to execute
            params (dict, optional): Query parameters. Defaults to None.
            fetch (bool, optional): Whether to fetch results. Defaults to True.
        
        Returns:
            list: Query results if fetch=True, otherwise None
        """
        return Database()._execute_query_impl(query, params, fetch)
        
    @staticmethod
    def execute_query_single(query, params=None):
        """Execute a query and fetch a single row
        
        Args:
            query (str): The SQL query to execute
            params (dict, optional): Query parameters. Defaults to None.
        
        Returns:
            tuple: A single row result or None if no results
        """
        return Database()._execute_query_single_impl(query, params)
        
    @staticmethod
    def execute_transaction(queries):
        """Execute multiple queries in a transaction"""
        return Database()._execute_transaction_impl(queries)
