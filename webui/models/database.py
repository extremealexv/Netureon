"""Database connection and ORM setup."""

import os
from flask import current_app, _app_ctx_stack
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import text

# Create the SQLAlchemy instance
db = SQLAlchemy()

class Database:
    """Database access class with SQLAlchemy integration."""
    
    @staticmethod
    def _ensure_context():
        """Ensure we have a valid application context."""
        if _app_ctx_stack.top is None:
            raise RuntimeError(
                "Working outside of application context. "
                "Make sure you are calling this from within a Flask route or have pushed an application context."
            )
    
    def _execute_query_impl(self, query, params=None, fetch=True):
        """Internal implementation of execute_query
        
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
        
        app = current_app._get_current_object()
        with app.app_context():
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
        self._ensure_context()
        if params is None:
            params = {}
            
        app = current_app._get_current_object()
        with app.app_context():
            result = db.session.execute(text(query), params)
            return result.fetchone()

    def _execute_transaction_impl(self, queries):
        """Internal implementation of execute_transaction"""
        self._ensure_context()
        app = current_app._get_current_object()
        
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
