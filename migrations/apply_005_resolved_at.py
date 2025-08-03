#!/usr/bin/env python3
"""Apply migration 005: Add resolved_at column to alerts table"""

import psycopg2
import os
from dotenv import load_dotenv

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
    """Apply the migration."""
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cursor = conn.cursor()

        with open('migrations/005_add_resolved_at.sql', 'r') as f:
            sql = f.read()
            cursor.execute(sql)
        
        conn.commit()
        print("Migration 005 applied successfully!")
        
        cursor.close()
        conn.close()
        
    except Exception as e:
        print(f"Error applying migration: {e}")
        return False
        
    return True

if __name__ == '__main__':
    apply_migration()
