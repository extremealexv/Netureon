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
        print(f"Error: {str(e)}")
        
        # Safe attribute access for diagnostic info
        if hasattr(e, 'diag'):
            diag = e.diag
            if hasattr(diag, 'message_primary'):
                print(f"Details: {diag.message_primary}")
            if hasattr(diag, 'message_detail'):
                print(f"Additional Info: {diag.message_detail}")
            if hasattr(diag, 'message_hint'):
                print(f"Hint: {diag.message_hint}")
            if hasattr(diag, 'context'):
                print(f"Context: {diag.context}")
        
        if 'conn' in locals() and conn:
            conn.rollback()
        raise
    except Exception as e:
        print(f"\n❌ Error during migration: {str(e)}")
        if 'conn' in locals() and conn:
            conn.rollback()
        raise
    finally:
        if 'cur' in locals() and cur:
            try:
                cur.close()
            except:
                pass
        if 'conn' in locals() and conn:
            try:
                conn.close()
            except:
                pass

if __name__ == "__main__":
    apply_migration()
