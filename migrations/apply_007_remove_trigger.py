#!/usr/bin/env python3
import psycopg2
from dotenv import load_dotenv
import os

load_dotenv()

# Database config
DB_CONFIG = {
    'dbname': os.getenv('DB_NAME', 'netguard'),
    'user': os.getenv('DB_USER', 'netguard'),
    'password': os.getenv('DB_PASSWORD', 'netguard'),
    'host': os.getenv('DB_HOST', 'localhost'),
    'port': os.getenv('DB_PORT', '5432')
}

def apply_migration():
    print("Removing automatic alert trigger and cleaning up duplicate alerts...")
    
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cursor = conn.cursor()
        
        with open('migrations/007_remove_alert_trigger.sql', 'r') as f:
            sql = f.read()
            
        cursor.execute(sql)
        conn.commit()
        
        print("Successfully removed alert trigger and cleaned up duplicate alerts")
        
    except Exception as e:
        print(f"Error applying migration: {e}")
        conn.rollback()
    finally:
        cursor.close()
        conn.close()

if __name__ == "__main__":
    apply_migration()
