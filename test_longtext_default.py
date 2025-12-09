#!/usr/bin/env python3
"""
Test specifically for LONGTEXT DEFAULT value handling on MySQL.
This tests the edge case where MySQL does not support DEFAULT values on TEXT/BLOB types,
but MariaDB does.
"""

import sqlite3
import mysql.connector
import os

def create_test_db_with_text_defaults():
    """Create SQLite database with TEXT columns that have DEFAULT values."""
    db_path = 'test_text_defaults.db'
    
    # Remove existing database if it exists
    if os.path.exists(db_path):
        os.remove(db_path)
        print(f"Removed existing {db_path}")
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    print(f"Creating test database: {db_path}")
    
    # Test case 1: TEXT with DEFAULT string value
    cursor.execute("""
        CREATE TABLE test_text_default (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name VARCHAR(255) DEFAULT 'test name',
            content TEXT DEFAULT 'default text content',
            description TEXT,
            status VARCHAR(50) DEFAULT 'active'
        )
    """)
    print("Created table: test_text_default")
    
    # Insert test data - some with values, some relying on defaults
    cursor.execute("""
        INSERT INTO test_text_default (name, content) 
        VALUES ('explicit', 'explicit content')
    """)
    
    cursor.execute("""
        INSERT INTO test_text_default (name, description) 
        VALUES ('default content', 'some description')
    """)
    
    # Test case 2: Different TEXT types with various defaults
    cursor.execute("""
        CREATE TABLE test_various_text (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            short_text VARCHAR(100) DEFAULT 'short',
            medium_text VARCHAR(500) DEFAULT 'medium text',
            long_text TEXT DEFAULT 'this is a very long default text that should be stored as LONGTEXT in MySQL',
            clob_text CLOB DEFAULT 'clob default',
            nullable_text TEXT,
            required_text TEXT NOT NULL
        )
    """)
    print("Created table: test_various_text")
    
    cursor.execute("""
        INSERT INTO test_various_text (required_text) 
        VALUES ('required value only')
    """)
    
    cursor.execute("""
        INSERT INTO test_various_text (short_text, long_text, required_text) 
        VALUES ('custom short', 'custom long', 'required')
    """)
    
    # Test case 3: Mixed column types with defaults
    cursor.execute("""
        CREATE TABLE test_mixed_defaults (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            int_col INTEGER DEFAULT 42,
            varchar_col VARCHAR(255) DEFAULT 'varchar default',
            text_col TEXT DEFAULT 'text default value',
            bool_col BOOLEAN DEFAULT 1,
            date_col DATETIME DEFAULT CURRENT_TIMESTAMP,
            blob_col BLOB
        )
    """)
    print("Created table: test_mixed_defaults")
    
    cursor.execute("""
        INSERT INTO test_mixed_defaults (varchar_col) 
        VALUES ('only varchar set')
    """)
    
    conn.commit()
    conn.close()
    
    print(f"\n✅ Test database created: {db_path}")
    
    # Show statistics
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = cursor.fetchall()
    
    print("\nDatabase statistics:")
    for table in tables:
        table_name = table[0]
        cursor.execute(f"SELECT COUNT(*) FROM `{table_name}`")
        count = cursor.fetchone()[0]
        print(f"  - {table_name}: {count} rows")
        
        # Show schema
        cursor.execute(f"PRAGMA table_info(`{table_name}`)")
        cols = cursor.fetchall()
        print(f"    Columns with defaults:")
        for col in cols:
            col_name, col_type, not_null, default_val = col[1], col[2], col[3], col[4]
            if default_val is not None:
                print(f"      • {col_name} ({col_type}): DEFAULT {default_val}")
    
    conn.close()
    return db_path

def run_migration_test(sqlite_db_path):
    """Run the migration and check for errors."""
    print("\n" + "="*80)
    print("RUNNING MIGRATION TO MYSQL")
    print("="*80 + "\n")
    
    # Import the migration function
    import sys
    sys.path.insert(0, '/Users/hmusanalli/github-projects/sqlite3tomysql')
    from migrate import migrate_sqlite_to_mysql
    
    mysql_config = {
        'host': 'localhost',
        'user': 'mysqluser',
        'password': 'changeme',
        'database': 'mysqldatabase'  # Use existing database
    }
    
    print(f"Using existing MySQL database: {mysql_config['database']}")
    print("Note: This will drop and recreate test tables in the existing database\n")
    
    # Run migration
    try:
        migrate_sqlite_to_mysql(sqlite_db_path, mysql_config)
        print("\n✅ Migration completed")
        return True
    except Exception as e:
        print(f"\n❌ Migration failed: {e}")
        return False

def verify_mysql_schema():
    """Verify that LONGTEXT columns don't have DEFAULT values on MySQL."""
    print("\n" + "="*80)
    print("VERIFYING MYSQL SCHEMA")
    print("="*80 + "\n")
    
    mysql_config = {
        'host': 'localhost',
        'user': 'mysqluser',
        'password': 'changeme',
        'database': 'mysqldatabase'  # Use existing database
    }
    
    try:
        conn = mysql.connector.connect(**mysql_config)
        cursor = conn.cursor()
        
        # Check server type
        cursor.execute("SELECT VERSION()")
        version = cursor.fetchone()[0]
        is_mysql = 'mariadb' not in version.lower()
        print(f"Server: {'MySQL' if is_mysql else 'MariaDB'} (version: {version})\n")
        
        # Get all tables
        cursor.execute("SHOW TABLES")
        tables = [t[0] for t in cursor.fetchall()]
        
        print("Checking DEFAULT values for TEXT/LONGTEXT columns:\n")
        
        issues_found = []
        successes = []
        
        for table in tables:
            cursor.execute(f"SHOW CREATE TABLE `{table}`")
            create_stmt = cursor.fetchone()[1]
            
            print(f"Table: `{table}`")
            print("-" * 80)
            
            # Get column details
            cursor.execute(f"DESCRIBE `{table}`")
            columns = cursor.fetchall()
            
            for col in columns:
                col_name, col_type, null, key, default, extra = col
                col_type_upper = col_type.upper()
                
                # Check if this is a TEXT/BLOB type
                is_text_blob = any(t in col_type_upper for t in ['TEXT', 'BLOB'])
                
                if is_text_blob:
                    if default is not None and default != 'NULL':
                        # This is an ERROR on MySQL
                        msg = f"  ❌ PROBLEM: `{col_name}` ({col_type}) has DEFAULT '{default}'"
                        print(msg)
                        issues_found.append(f"{table}.{col_name}: {col_type} with DEFAULT {default}")
                    else:
                        msg = f"  ✅ CORRECT: `{col_name}` ({col_type}) has no DEFAULT"
                        print(msg)
                        successes.append(f"{table}.{col_name}: {col_type}")
                elif default is not None:
                    print(f"  ℹ️  OK: `{col_name}` ({col_type}) DEFAULT {default}")
            
            print()
        
        print("="*80)
        print("SUMMARY")
        print("="*80)
        print(f"\n✅ Correct TEXT/BLOB columns (no DEFAULT): {len(successes)}")
        for s in successes:
            print(f"   - {s}")
        
        if issues_found:
            print(f"\n❌ Problematic TEXT/BLOB columns (has DEFAULT): {len(issues_found)}")
            for issue in issues_found:
                print(f"   - {issue}")
            print("\n⚠️  These DEFAULT values will cause Error 1101 on MySQL!")
        else:
            print("\n✅ No issues found! All TEXT/BLOB columns correctly have no DEFAULT values on MySQL.")
        
        # Test data integrity
        print("\n" + "="*80)
        print("DATA INTEGRITY CHECK")
        print("="*80 + "\n")
        
        for table in tables:
            cursor.execute(f"SELECT COUNT(*) FROM `{table}`")
            count = cursor.fetchone()[0]
            print(f"Table `{table}`: {count} rows")
            
            if count > 0:
                cursor.execute(f"SELECT * FROM `{table}` LIMIT 2")
                rows = cursor.fetchall()
                cursor.execute(f"DESCRIBE `{table}`")
                col_names = [c[0] for c in cursor.fetchall()]
                
                print(f"  Sample data:")
                for row in rows:
                    row_data = dict(zip(col_names, row))
                    for key, val in row_data.items():
                        if val is not None and len(str(val)) > 50:
                            val = str(val)[:50] + "..."
                        print(f"    {key}: {val}")
                    print()
        
        cursor.close()
        conn.close()
        
        return len(issues_found) == 0
        
    except mysql.connector.Error as e:
        print(f"❌ Error verifying MySQL schema: {e}")
        return False

if __name__ == "__main__":
    print("="*80)
    print("TEST: LONGTEXT DEFAULT VALUE HANDLING ON MYSQL")
    print("="*80 + "\n")
    
    # Step 1: Create test database
    db_path = create_test_db_with_text_defaults()
    
    # Step 2: Run migration
    if run_migration_test(db_path):
        # Step 3: Verify schema
        success = verify_mysql_schema()
        
        if success:
            print("\n" + "="*80)
            print("✅ TEST PASSED: LONGTEXT columns correctly have no DEFAULT on MySQL")
            print("="*80)
        else:
            print("\n" + "="*80)
            print("❌ TEST FAILED: Some LONGTEXT columns incorrectly have DEFAULT values")
            print("="*80)
    else:
        print("\n❌ Migration failed, cannot verify schema")
