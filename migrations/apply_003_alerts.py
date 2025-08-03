#!/usr/bin/env python3
import os
import psycopg2
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Database configuration
DB_CONFIG = {
    'dbname': os.getenv('DB_NAME'),
    'user': os.getenv('DB_USER'),
    'password': os.getenv('DB_PASSWORD'),
    'host': os.getenv('DB_HOST'),
    'port': os.getenv('DB_PORT')
}

def apply_migration():
    """Apply the alerts table migration."""
    print("Applying alerts table migration...")
    
    try:
        # Connect to the database
        conn = psycopg2.connect(**DB_CONFIG)
        cur = conn.cursor()
        
        # Read and execute the migration script
        with open('migrations/003_alerts_table.sql', 'r') as f:
            migration_sql = f.read()
            
        cur.execute(migration_sql)
        
        # Verify the new table structure
        cur.execute("""
            SELECT column_name, data_type, is_nullable
            FROM information_schema.columns
            WHERE table_name = 'alerts'
            ORDER BY ordinal_position;
        """)
        
        print("\nNew alerts table structure:")
        for column in cur.fetchall():
            print(f"  {column[0]:<15} {column[1]:<15} {column[2]}")
            
        # Get the number of migrated alerts if any
        cur.execute("SELECT COUNT(*) FROM alerts")
        count = cur.fetchone()[0]
        print(f"\nMigrated {count} existing alerts")
        
        # Commit the transaction
        conn.commit()
        print("\n✅ Migration completed successfully!")
        
    except psycopg2.Error as e:
        print(f"\n❌ Database error during migration:")
        print(f"Error: {e.diag.message_primary if hasattr(e, 'diag') else str(e)}")
        if hasattr(e, 'diag'):
            if e.diag.context:
                print(f"Context: {e.diag.context}")
            if e.diag.statement:
                print(f"Statement: {e.diag.statement}")
        conn.rollback()
        raise
    except Exception as e:
        print(f"\n❌ Error during migration: {str(e)}")
        conn.rollback()
        raise
    finally:
        if 'cur' in locals() and cur:
            cur.close()
        if 'conn' in locals() and conn:
            conn.close()

if __name__ == "__main__":
    apply_migration()
