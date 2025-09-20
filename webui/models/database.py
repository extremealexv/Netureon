"""Database connection and ORM setup."""

from flask import current_app
from sqlalchemy import text, bindparam
from flask_sqlalchemy import SQLAlchemy
import logging
import psycopg2
from contextlib import contextmanager

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
            
        # Use SQLAlchemy's bindparams for proper parameter binding
        stmt = text(query)
        if params:
            for key, value in params.items():
                stmt = stmt.bindparams(bindparam(key))
                
        result = db.session.execute(stmt, params)
        if fetch:
            return result.fetchall()
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
        # Use SQLAlchemy's bindparams for proper parameter binding
        stmt = text(query)
        if params:
            for key, value in params.items():
                stmt = stmt.bindparams(bindparam(key))
        result = db.session.execute(stmt, params)
        return result.fetchone()

    def _execute_transaction_impl(self, queries):
        """Execute multiple queries in a transaction.
        
        Args:
            queries (list): List of tuples containing (query, params) pairs
                where params can be a dict or tuple
        """
        self._ensure_context()
        
        results = []
        try:
            for query, params in queries:
                if params is None:
                    params = {}
                elif isinstance(params, tuple):
                    # Convert tuple parameters to a dict format
                    params = {f"param_{i}": val for i, val in enumerate(params)}
                    
                # Use SQLAlchemy's text() with proper parameter binding
                stmt = text(query)
                if params:
                    for key, value in params.items():
                        stmt = stmt.bindparams(bindparam(key))
                result = db.session.execute(stmt, params)
                results.append(result)
                
            db.session.commit()
            return results
            
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
        try:
            with Database.get_connection() as conn:
                with conn.cursor() as cur:
                    result = None
                    for query, params in queries:
                        # Convert tuple parameters to proper format
                        if isinstance(params, tuple):
                            # If tuple has only one element, unpack it
                            if len(params) == 1:
                                params = params[0]
                        
                        # Log for debugging
                        logging.debug(f"Executing query: {query}")
                        logging.debug(f"With parameters: {params}")
                        
                        cur.execute(query, params)
                        
                        try:
                            result = cur.fetchall()
                        except psycopg2.ProgrammingError:
                            # No results to fetch
                            pass
                            
                    conn.commit()
                    return result
                    
        except Exception as e:
            if 'conn' in locals():
                conn.rollback()
            logging.error(f"Transaction failed: {str(e)}\nQuery: {query}\nParams: {params}")
            raise
