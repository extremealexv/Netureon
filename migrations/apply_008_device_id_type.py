#!/usr/bin/env python3
"""Apply migration 008: Fix device_id type in alerts table"""

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
    print("📦 Applying migration 008: Fix device_id type in alerts table")
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cur = conn.cursor()
        
        # Read and execute the SQL file
        with open('migrations/008_fix_device_id_type.sql', 'r') as f:
            sql = f.read()
            cur.execute(sql)
        
        conn.commit()
        cur.close()
        conn.close()
        print("✅ Migration applied successfully")
        
    except Exception as e:
        print(f"❌ Error applying migration: {e}")
        raise

if __name__ == '__main__':
    apply_migration()
