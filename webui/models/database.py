import psycopg2
from config.config import Config

class Database:
    @staticmethod
    def get_connection():
        return psycopg2.connect(**Config.DB_CONFIG)

    @staticmethod
    def execute_query(query, params=None, fetch=True):
        """Execute a query and optionally fetch results
        
        Args:
            query (str): The SQL query to execute
            params (tuple, optional): Query parameters. Defaults to None.
            fetch (bool, optional): Whether to fetch results. Defaults to True.
        
        Returns:
            list: Query results if fetch=True, otherwise None
        """
        conn = Database.get_connection()
        cur = conn.cursor()
        try:
            cur.execute(query, params)
            if fetch:
                result = cur.fetchall()
            else:
                result = None
                if cur.statusmessage.startswith('DELETE') or cur.statusmessage.startswith('UPDATE'):
                    result = cur.rowcount
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
