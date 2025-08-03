import psycopg2
import os
from dotenv import load_dotenv

def apply_migration():
    load_dotenv()
    
    # Get database connection details from environment variables
    db_config = {
        'dbname': os.getenv('DB_NAME'),
        'user': os.getenv('DB_USER'),
        'password': os.getenv('DB_PASSWORD'),
        'host': os.getenv('DB_HOST'),
        'port': os.getenv('DB_PORT')
    }
    
    try:
        # Connect to the database
        conn = psycopg2.connect(**db_config)
        cur = conn.cursor()
        
        # Read and execute the SQL migration file
        with open('migrations/004_fix_alert_trigger.sql', 'r') as f:
            migration_sql = f.read()
            cur.execute(migration_sql)
        
        # Commit the changes
        conn.commit()
        print("✅ Successfully updated alert trigger function")
        
    except Exception as e:
        print(f"❌ Error applying migration: {str(e)}")
        conn.rollback()
        raise
    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()

if __name__ == "__main__":
    apply_migration()
