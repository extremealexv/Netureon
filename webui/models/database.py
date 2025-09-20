"""Database connection and ORM setup."""

from flask import current_app
from flask_sqlalchemy import SQLAlchemy
import psycopg2
import psycopg2.extras
import logging
from contextlib import contextmanager

logger = logging.getLogger(__name__)

db = SQLAlchemy()

class Database:
    @staticmethod
    def get_connection():
        """Get a database connection using Flask config."""
        try:
            return psycopg2.connect(
                dbname=current_app.config['DB_NAME'],
                user=current_app.config['DB_USER'],
                password=current_app.config['DB_PASSWORD'],
                host=current_app.config['DB_HOST'],
                port=current_app.config['DB_PORT']
            )
        except Exception as e:
            logger.error(f"Database connection failed: {str(e)}")
            raise

    @staticmethod
    def execute_transaction(queries):
        """Execute multiple queries in a transaction."""
        connection = None
        try:
            connection = Database.get_connection()
            # Use DictCursor for better parameter handling
            cursor = connection.cursor(cursor_factory=psycopg2.extras.DictCursor)
            
            results = []
            for query, params in queries:
                logger.debug(f"Executing query: {query}")
                logger.debug(f"Parameters: {params}")
                
                # Convert tuple parameters to list
                if isinstance(params, tuple):
                    params = list(params)
                
                try:
                    cursor.execute(query, params)
                    try:
                        result = cursor.fetchall()
                        results.append(result)
                    except psycopg2.ProgrammingError:
                        results.append(None)
                except Exception as qe:
                    logger.error(f"Query execution failed: {str(qe)}")
                    logger.error(f"Query: {cursor.query.decode()}")
                    raise
            
            connection.commit()
            return results
            
        except Exception as e:
            logger.error(f"Transaction failed: {str(e)}")
            if connection:
                connection.rollback()
            raise
        finally:
            if connection:
                connection.close()

    @staticmethod
    def execute_query(query, params=None):
        """Execute a single query."""
        with Database.get_connection() as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
                cur.execute(query, params)
                try:
                    return cur.fetchall()
                except psycopg2.ProgrammingError:
                    return None
