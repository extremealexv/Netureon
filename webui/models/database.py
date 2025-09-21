"""Database connection and ORM setup."""

from flask import current_app
from flask_sqlalchemy import SQLAlchemy
import psycopg2
import psycopg2.extras
import logging

db = SQLAlchemy()

class Database:
    logger = logging.getLogger(__name__)
    
    @classmethod
    def get_connection(cls):
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
            cls.logger.error(f"Database connection failed: {str(e)}")
            raise

    @classmethod
    def execute_query(cls, query, params=None):
        cls.logger.debug(f"Executing query: {query}")
        cls.logger.debug(f"Parameters: {params}")
        """Execute a SQL query and return results."""
        try:
            with cls.get_connection() as conn:
                with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
                    cur.execute(query, params)
                    try:
                        return cur.fetchall()
                    except psycopg2.ProgrammingError:
                        return None
        except Exception as e:
            cls.logger.error(f"Query execution failed: {str(e)}")
            cls.logger.error(f"Query: {query}")
            cls.logger.error(f"Params: {params}")
            raise

    @staticmethod
    def execute_transaction(queries):
        """Execute multiple queries in a transaction."""
        connection = None
        try:
            connection = Database.get_connection()
            cursor = connection.cursor(cursor_factory=psycopg2.extras.DictCursor)
            
            results = []
            for query, params in queries:
                logger.debug(f"Executing query: {query}")
                logger.debug(f"Parameters: {params}")
                
                cursor.execute(query, params)
                try:
                    result = cursor.fetchall()
                    results.append(result)
                except psycopg2.ProgrammingError:
                    results.append(None)
            
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
