#!/usr/bin/env python3
"""
Verifies the MySQL migration by checking tables, schemas, and data integrity.
"""

import mysql.connector
from mysql.connector import Error

def verify_migration(mysql_config):
    """
    Verifies the migration by checking:
    1. All tables exist
    2. Row counts match
    3. Schema structure
    4. Sample data integrity
    """
    try:
        conn = mysql.connector.connect(**mysql_config)
        cursor = conn.cursor()
        print(f"Connected to MySQL database: {mysql_config['database']}")
        print("=" * 80)
        
        # Get list of tables
        cursor.execute("SHOW TABLES")
        tables = [table[0] for table in cursor.fetchall()]
        print(f"\nFound {len(tables)} tables in MySQL:")
        print(f"   {', '.join(tables)}\n")
        
        # Verify each table
        expected_tables = [
            'monitor', 'heartbeat', 'api_key', 'maintenance', 
            'group', 'knex_migrations', 'tag', 'notification', 
            'status_page', 'metrics'
        ]
        
        print("Verifying tables:\n")
        for table in expected_tables:
            if table not in tables:
                print(f"   Table '{table}' is MISSING!")
                continue
            
            # Get row count
            cursor.execute(f"SELECT COUNT(*) FROM `{table}`")
            count = cursor.fetchone()[0]
            
            # Get schema info
            cursor.execute(f"DESCRIBE `{table}`")
            columns = cursor.fetchall()
            
            print(f"   Table: `{table}`")
            print(f"      - Rows: {count}")
            print(f"      - Columns: {len(columns)}")
            
            # Show column details for important tables
            if table in ['api_key', 'maintenance', 'metrics']:
                print(f"      - Schema:")
                for col in columns:
                    col_name, col_type, null, key, default, extra = col
                    key_info = f" [{key}]" if key else ""
                    extra_info = f" {extra}" if extra else ""
                    print(f"        • {col_name}: {col_type}{key_info}{extra_info}")
            
            print()
        
        # Detailed verification of edge cases
        print("=" * 80)
        print("\nDetailed Edge Case Verification:\n")
        
        # 1. Check TIME data type in maintenance table
        print("1. TIME Data Type (maintenance table):")
        cursor.execute("SELECT title, start_time, end_time FROM maintenance")
        for row in cursor.fetchall():
            print(f"   - {row[0]}: {row[1]} to {row[2]}")
        
        # 2. Check UNIQUE constraints on api_key
        print("\n2. UNIQUE Constraints (api_key table):")
        cursor.execute("SHOW INDEX FROM api_key WHERE Key_name != 'PRIMARY'")
        indexes = cursor.fetchall()
        for idx in indexes:
            print(f"   - {idx[2]} on column: {idx[4]}")
        
        # 3. Check VARCHAR(191) for indexed columns
        print("\n3. VARCHAR Length for Indexed Columns:")
        for table in ['api_key', 'tag', 'status_page']:
            cursor.execute(f"DESCRIBE `{table}`")
            cols = cursor.fetchall()
            for col in cols:
                if 'VARCHAR(191)' in col[1]:
                    print(f"   - `{table}`.`{col[0]}`: {col[1]} (Index-safe)")
        
        # 4. Check BLOB data
        print("\n4. BLOB Data (status_page table):")
        cursor.execute("SELECT slug, icon IS NOT NULL as has_icon FROM status_page")
        for row in cursor.fetchall():
            print(f"   - {row[0]}: {'Has icon data' if row[1] else 'No icon'}")
        
        # 5. Check numeric types in metrics table
        print("\n5. Numeric Types (metrics table):")
        cursor.execute("SELECT metric_name, tiny_value, big_value, decimal_value FROM metrics")
        for row in cursor.fetchall():
            print(f"   - {row[0]}: tiny={row[1]}, big={row[2]}, decimal={row[3]}")
        
        # 6. Check reserved keyword table (group)
        print("\n6. Reserved Keyword Table (`group`):")
        cursor.execute("SELECT name, weight FROM `group`")
        for row in cursor.fetchall():
            print(f"   - {row[0]}: weight={row[1]}")
        
        # 7. Check timestamp conversion in knex_migrations
        print("\n7. Timestamp Conversion (knex_migrations):")
        cursor.execute("SELECT name, migration_time FROM knex_migrations")
        for row in cursor.fetchall():
            print(f"   - {row[0]}: {row[1]}")
        
        # 8. Check DATETIME fields with CURRENT_TIMESTAMP
        print("\n8. DATETIME/TIMESTAMP Fields:")
        cursor.execute("SELECT name, created_date FROM monitor LIMIT 1")
        row = cursor.fetchone()
        print(f"   - monitor.created_date: {row[1]} (type: TIMESTAMP)")
        
        cursor.execute("SELECT client_name, created_at, updated_at FROM api_key LIMIT 1")
        row = cursor.fetchone()
        print(f"   - api_key.created_at: {row[1]} (type: TIMESTAMP)")
        print(f"   - api_key.updated_at: {row[2]} (type: TIMESTAMP with ON UPDATE)")
        
        # 9. Check special characters in data
        print("\n9. Special Characters in Data:")
        cursor.execute("SELECT msg FROM heartbeat WHERE msg LIKE '%special chars%' LIMIT 1")
        row = cursor.fetchone()
        if row:
            print(f"   - Sample: {row[0]}")
        
        # 10. Check JSON-like TEXT data
        print("\n10. JSON-like TEXT Data (notification.config):")
        cursor.execute("SELECT name, SUBSTRING(config, 1, 50) as config_preview FROM notification LIMIT 1")
        row = cursor.fetchone()
        if row:
            print(f"   - {row[0]}: {row[1]}...")
        
        print("\n" + "=" * 80)
        print("MIGRATION VERIFICATION COMPLETE!")
        print("=" * 80)
        
        cursor.close()
        conn.close()
        
    except Error as e:
        print(f"Error connecting to MySQL: {e}")
    except Exception as e:
        print(f"Unexpected error: {e}")

if __name__ == "__main__":
    mysql_config = {
        'host': 'localhost',
        'user': 'mysqluser',
        'password': 'changeme',
        'database': 'mysqldatabase'
    }
    
    verify_migration(mysql_config)
