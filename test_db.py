import psycopg2
from psycopg2 import OperationalError

def test_postgres_connection(host, port, dbname, user, password):
    try:
        print(f"🔌 Attempting to connect to PostgreSQL at {host}:{port}...")
        conn = psycopg2.connect(
            host=host,
            port=port,
            dbname=dbname,
            user=user,
            password=password,
            connect_timeout=5
        )
        print("✅ Connection successful!")
        conn.close()
    except OperationalError as e:
        print("❌ Connection failed.")
        print(f"Error details:\n{e}")

# 🔧 Replace these with your actual credentials
host = "192.168.1.60"
port = 5432
dbname = "netguard"
user = "postgres"
password = "N#hbv4c2ff"

test_postgres_connection(host, port, dbname, user, password)
