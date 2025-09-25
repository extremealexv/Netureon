#!/usr/bin/env python3
"""
Quick diagnostic script to check the actual database table structures.
"""

import sys
import os
import psycopg2
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def check_table_structure(table_name):
    """Check the structure of a specific table."""
    try:
        db_config = {
            'dbname': os.getenv('DB_NAME'),
            'user': os.getenv('DB_USER'),
            'password': os.getenv('DB_PASSWORD'),
            'host': os.getenv('DB_HOST'),
            'port': os.getenv('DB_PORT')
        }
        
        with psycopg2.connect(**db_config) as conn:
            with conn.cursor() as cursor:
                cursor.execute("""
                    SELECT column_name, data_type, is_nullable, column_default
                    FROM information_schema.columns 
                    WHERE table_name = %s 
                    ORDER BY ordinal_position
                """, (table_name,))
                
                columns = cursor.fetchall()
                
                print(f"\n=== {table_name.upper()} TABLE STRUCTURE ===")
                if columns:
                    for col_name, data_type, nullable, default in columns:
                        nullable_str = "NULL" if nullable == "YES" else "NOT NULL"
                        default_str = f" DEFAULT {default}" if default else ""
                        print(f"  {col_name:<20} {data_type:<15} {nullable_str}{default_str}")
                else:
                    print(f"  Table '{table_name}' not found or has no columns")
                
                return len(columns) > 0
                
    except Exception as e:
        print(f"Error checking {table_name}: {e}")
        return False

def check_recent_data(table_name, limit=5):
    """Check recent data in a table."""
    try:
        db_config = {
            'dbname': os.getenv('DB_NAME'),
            'user': os.getenv('DB_USER'),
            'password': os.getenv('DB_PASSWORD'),
            'host': os.getenv('DB_HOST'),
            'port': os.getenv('DB_PORT')
        }
        
        with psycopg2.connect(**db_config) as conn:
            with conn.cursor() as cursor:
                cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
                count = cursor.fetchone()[0]
                
                print(f"\n=== {table_name.upper()} DATA ===")
                print(f"  Total records: {count}")
                
                if count > 0:
                    cursor.execute(f"SELECT * FROM {table_name} ORDER BY id DESC LIMIT %s", (limit,))
                    rows = cursor.fetchall()
                    
                    if rows:
                        print(f"  Recent {len(rows)} records:")
                        for i, row in enumerate(rows, 1):
                            print(f"    {i}: {row}")
                
    except Exception as e:
        print(f"Error checking data in {table_name}: {e}")

def main():
    """Main diagnostic function."""
    print("Netureon Database Structure Diagnostic")
    print("=" * 40)
    
    tables_to_check = ['alerts', 'new_devices', 'known_devices', 'unknown_devices', 'configuration']
    
    for table in tables_to_check:
        if check_table_structure(table):
            check_recent_data(table, 3)
    
    print("\n" + "=" * 40)
    print("Diagnostic complete!")

if __name__ == "__main__":
    main()