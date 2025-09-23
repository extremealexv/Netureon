"""Database connection and ORM setup."""

import os
import logging
from flask import current_app
from flask_sqlalchemy import SQLAlchemy
import psycopg2
from psycopg2.extras import DictCursor

db = SQLAlchemy()

logger = logging.getLogger(__name__)

class Database:
    @classmethod
    def get_connection(cls):
        """Get database connection with proper configuration."""
        try:
            conn = psycopg2.connect(
                dbname="netguard",
                user="postgres",
                password="your_password",  # Replace with actual password
                host="localhost",
                port="5432"
            )
            return conn
        except Exception as e:
            logger.error(f"Database connection failed: {str(e)}")
            raise

    @classmethod
    def execute_query(cls, query, params=None):
        logger.debug(f"Executing query: {query}")
        logger.debug(f"Parameters: {params}")
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
            logger.error(f"Query execution failed: {str(e)}")
            logger.error(f"Query: {query}")
            logger.error(f"Params: {params}")
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
