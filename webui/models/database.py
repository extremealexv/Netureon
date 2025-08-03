import psycopg2
from config.config import Config

class Database:
    @staticmethod
    def get_connection():
        return psycopg2.connect(**Config.DB_CONFIG)

    @staticmethod
    def execute_query(query, params=None):
        conn = Database.get_connection()
        cur = conn.cursor()
        try:
            cur.execute(query, params)
            result = cur.fetchall()
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
