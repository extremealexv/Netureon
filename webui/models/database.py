"""Database connection and ORM setup."""

import os
from contextlib import contextmanager
from flask import current_app
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import text

# Create the SQLAlchemy instance
db = SQLAlchemy()

class Database:
    """Database access class with SQLAlchemy integration."""
    
    @contextmanager
    def _app_context(self):
        """Context manager for Flask application context."""
        try:
            # Try to get the current app context
            current_app._get_current_object()
            yield
        except RuntimeError:
            # If no app context exists, use current_app's context
            with current_app.app_context():
                yield

    def _execute_query_impl(self, query, params=None, fetch=True):
        """Internal implementation of execute_query
        
        Args:
            query (str): The SQL query to execute
            params (dict, optional): Query parameters. Defaults to None.
            fetch (bool, optional): Whether to fetch results. Defaults to True.
        
        Returns:
            list: Query results if fetch=True, otherwise None
        """
        with self._app_context():
            if params is None:
                params = {}
            result = db.session.execute(text(query), params)
            if fetch:
                return result.fetchall()
            db.session.commit()
            return result.rowcount if result.rowcount > -1 else None

    def _execute_query_single_impl(self, query, params=None):
        """Internal implementation of execute_query_single
        
        Args:
            query (str): The SQL query to execute
            params (dict, optional): Query parameters. Defaults to None.
        
        Returns:
            tuple: A single row result or None if no results
        """
        with self._app_context():
            if params is None:
                params = {}
            result = db.session.execute(text(query), params)
            return result.fetchone()

    def _execute_transaction_impl(self, queries):
        """Internal implementation of execute_transaction"""
        with self._app_context():
            try:
                for query, params in queries:
                    if params is None:
                        params = {}
                    db.session.execute(text(query), params)
                db.session.commit()
            except Exception as e:
                db.session.rollback()
                raise e

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
