"""Database connection and ORM setup."""

from flask import current_app
from flask_sqlalchemy import SQLAlchemy
import psycopg2
import psycopg2.extras
import logging

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
    def execute_query(query, params=None):
        """Execute a SQL query and return results."""
        try:
            with Database.get_connection() as conn:
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
