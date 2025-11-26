# code to remove database and all data - should not be run unless essential

import os
import sys
import psycopg2
from psycopg2 import sql

# Import centralized configuration
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config

# Use centralized database configuration
DB_CONFIG = config.DB_CONFIG

def wipe_database():
    """
    Drops all tables, sequences, and custom types from the database.
    This operation is IRREVERSIBLE.
    """
    
    # Safety confirmation
    confirmation = input(f"WARNING: This will permanently delete ALL data from {DB_CONFIG['database']}.\n"
                        f"Type 'DELETE EVERYTHING' to proceed: ")
    
    if confirmation != "DELETE EVERYTHING":
        print("Operation cancelled.")
        return
    
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        conn.autocommit = True
        cur = conn.cursor()
        
        # Get all tables in public schema
        cur.execute("""
            SELECT tablename 
            FROM pg_tables 
            WHERE schemaname = 'public'
        """)
        tables = cur.fetchall()
        
        # Drop all tables with CASCADE
        for table in tables:
            table_name = table[0]
            cur.execute(sql.SQL("DROP TABLE IF EXISTS {} CASCADE").format(
                sql.Identifier(table_name)
            ))
            print(f"Dropped table: {table_name}")
        
        # Drop sequences
        cur.execute("""
            SELECT sequence_name 
            FROM information_schema.sequences 
            WHERE sequence_schema = 'public'
        """)
        sequences = cur.fetchall()
        
        for seq in sequences:
            seq_name = seq[0]
            cur.execute(sql.SQL("DROP SEQUENCE IF EXISTS {} CASCADE").format(
                sql.Identifier(seq_name)
            ))
            print(f"Dropped sequence: {seq_name}")
        
        print("\nDatabase wiped successfully.")
        
    except Exception as e:
        print(f"Error: {e}")
    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()

if __name__ == "__main__":
    wipe_database()