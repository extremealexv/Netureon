"""Database connection and ORM setup."""

from flask import current_app
from sqlalchemy import text
from flask_sqlalchemy import SQLAlchemy

# Create the SQLAlchemy instance
db = SQLAlchemy()

class Database:
    """Database access class with SQLAlchemy integration."""
    
    def _ensure_context(self):
        """Ensure we have a valid application context."""
        if not current_app:
            raise RuntimeError(
                "No application context found. "
                "Ensure you're within a Flask request or application context."
            )
    
    def _execute_query_impl(self, query, params=None, fetch=True):
        """Execute a query and optionally fetch results.
        
        Args:
            query (str): The SQL query to execute
            params (dict, optional): Query parameters. Defaults to None.
            fetch (bool, optional): Whether to fetch results. Defaults to True.
        
        Returns:
            list: Query results if fetch=True, otherwise None
        """
        self._ensure_context()
        if params is None:
            params = {}
        result = db.session.execute(text(query), params)
        if fetch:
            return result.fetchall()
        db.session.commit()
        return result.rowcount if result.rowcount > -1 else None

    def _execute_query_single_impl(self, query, params=None):
        """Execute a query and fetch a single row.
        
        Args:
            query (str): The SQL query to execute
            params (dict, optional): Query parameters. Defaults to None.
        
        Returns:
            tuple: A single row result or None if no results
        """
        self._ensure_context()
        if params is None:
            params = {}
        result = db.session.execute(text(query), params)
        return result.fetchone()

    def _execute_transaction_impl(self, queries):
        """Execute multiple queries in a transaction."""
        self._ensure_context()
        try:
            for query, params in queries:
                if params is None:
                    params = {}
                db.session.execute(text(query), params)
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            raise e

    @staticmethod
    def execute_query(query, params=None, fetch=True):
        """Execute a query and optionally fetch results.
        
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
        """Execute a query and fetch a single row.
        
        Args:
            query (str): The SQL query to execute
            params (dict, optional): Query parameters. Defaults to None.
        
        Returns:
            tuple: A single row result or None if no results
        """
        return Database()._execute_query_single_impl(query, params)
        
    @staticmethod
    def execute_transaction(queries):
        """Execute multiple queries in a transaction."""
        return Database()._execute_transaction_impl(queries)
