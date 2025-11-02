#!/usr/bin/env python3
"""
SQLite3 to MySQL/MariaDB Migration Script

This script migrates data from SQLite3 databases to MySQL/MariaDB.
Based on: https://medium.com/@gadallah.hatem/seamlessly-migrating-sqlite-databases-to-mysql-a-comprehensive-python-guide-f8776f50e356

Tested with UptimeKuma migration (v2 onwards).
Requires: mysql-connector-python
"""

import sqlite3
import mysql.connector
import argparse
import sys
from typing import List, Tuple, Optional


class SQLiteToMySQLMigrator:
    """Handles migration from SQLite3 to MySQL/MariaDB."""
    
    def __init__(self, sqlite_db_path: str, mysql_config: dict):
        """
        Initialize the migrator.
        
        Args:
            sqlite_db_path: Path to SQLite database file
            mysql_config: Dictionary with MySQL connection parameters
                         (host, user, password, database)
        """
        self.sqlite_db_path = sqlite_db_path
        self.mysql_config = mysql_config
        self.sqlite_conn = None
        self.mysql_conn = None
        
    def connect(self):
        """Establish connections to both databases."""
        try:
            # Connect to SQLite
            self.sqlite_conn = sqlite3.connect(self.sqlite_db_path)
            print(f"✓ Connected to SQLite database: {self.sqlite_db_path}")
            
            # Connect to MySQL
            self.mysql_conn = mysql.connector.connect(**self.mysql_config)
            print(f"✓ Connected to MySQL database: {self.mysql_config.get('database', 'N/A')}")
            
        except sqlite3.Error as e:
            print(f"✗ SQLite connection error: {e}")
            sys.exit(1)
        except mysql.connector.Error as e:
            print(f"✗ MySQL connection error: {e}")
            sys.exit(1)
    
    def close(self):
        """Close database connections."""
        if self.sqlite_conn:
            self.sqlite_conn.close()
            print("✓ Closed SQLite connection")
        if self.mysql_conn:
            self.mysql_conn.close()
            print("✓ Closed MySQL connection")
    
    def get_sqlite_tables(self) -> List[str]:
        """
        Get list of tables from SQLite database.
        
        Returns:
            List of table names
        """
        cursor = self.sqlite_conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%';")
        tables = [row[0] for row in cursor.fetchall()]
        cursor.close()
        return tables
    
    def get_table_schema(self, table_name: str) -> List[Tuple]:
        """
        Get schema information for a table from SQLite.
        
        Args:
            table_name: Name of the table
            
        Returns:
            List of tuples with column information (cid, name, type, notnull, dflt_value, pk)
        """
        cursor = self.sqlite_conn.cursor()
        cursor.execute(f"PRAGMA table_info({table_name});")
        schema = cursor.fetchall()
        cursor.close()
        return schema
    
    def sqlite_to_mysql_type(self, sqlite_type: str) -> str:
        """
        Convert SQLite data type to MySQL data type.
        
        Args:
            sqlite_type: SQLite data type
            
        Returns:
            Corresponding MySQL data type
        """
        sqlite_type = sqlite_type.upper()
        
        type_mapping = {
            'INTEGER': 'INT',
            'TEXT': 'TEXT',
            'REAL': 'DOUBLE',
            'BLOB': 'BLOB',
            'NUMERIC': 'NUMERIC',
            'VARCHAR': 'VARCHAR',
            'CHAR': 'CHAR',
            'DATETIME': 'DATETIME',
            'DATE': 'DATE',
            'TIME': 'TIME',
            'TIMESTAMP': 'TIMESTAMP',
            'BOOLEAN': 'TINYINT(1)',
            'BIGINT': 'BIGINT',
            'FLOAT': 'FLOAT',
            'DOUBLE': 'DOUBLE',
        }
        
        # Check if the type contains parameters (e.g., VARCHAR(255))
        for sqlite_key, mysql_type in type_mapping.items():
            if sqlite_type.startswith(sqlite_key):
                # Preserve parameters if they exist
                if '(' in sqlite_type:
                    params = sqlite_type[sqlite_type.index('('):]
                    return mysql_type.split('(')[0] + params
                return mysql_type
        
        # Default to TEXT for unknown types
        return 'TEXT'
    
    def create_mysql_table(self, table_name: str, schema: List[Tuple]):
        """
        Create table in MySQL based on SQLite schema.
        
        Args:
            table_name: Name of the table to create
            schema: Schema information from SQLite
        """
        cursor = self.mysql_conn.cursor()
        
        # Build CREATE TABLE statement
        columns = []
        primary_keys = []
        
        for col in schema:
            col_id, col_name, col_type, not_null, default_val, is_pk = col
            
            mysql_type = self.sqlite_to_mysql_type(col_type if col_type else 'TEXT')
            
            col_def = f"`{col_name}` {mysql_type}"
            
            if not_null:
                col_def += " NOT NULL"
            
            if default_val is not None:
                col_def += f" DEFAULT {default_val}"
            
            if is_pk:
                primary_keys.append(col_name)
            
            columns.append(col_def)
        
        # Add primary key constraint if exists
        if primary_keys:
            pk_cols = ", ".join([f"`{pk}`" for pk in primary_keys])
            columns.append(f"PRIMARY KEY ({pk_cols})")
        
        create_table_sql = f"CREATE TABLE IF NOT EXISTS `{table_name}` ({', '.join(columns)}) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;"
        
        try:
            cursor.execute(create_table_sql)
            self.mysql_conn.commit()
            print(f"  ✓ Created table: {table_name}")
        except mysql.connector.Error as e:
            print(f"  ✗ Error creating table {table_name}: {e}")
            print(f"  SQL: {create_table_sql}")
        finally:
            cursor.close()
    
    def migrate_table_data(self, table_name: str):
        """
        Migrate data from SQLite table to MySQL table.
        
        Args:
            table_name: Name of the table to migrate
        """
        sqlite_cursor = self.sqlite_conn.cursor()
        mysql_cursor = self.mysql_conn.cursor()
        
        try:
            # Get all data from SQLite table
            sqlite_cursor.execute(f"SELECT * FROM `{table_name}`;")
            rows = sqlite_cursor.fetchall()
            
            if not rows:
                print(f"  ✓ No data to migrate for table: {table_name}")
                return
            
            # Get column count
            column_count = len(rows[0])
            placeholders = ', '.join(['%s'] * column_count)
            
            # Insert data into MySQL
            insert_sql = f"INSERT INTO `{table_name}` VALUES ({placeholders})"
            
            mysql_cursor.executemany(insert_sql, rows)
            self.mysql_conn.commit()
            
            print(f"  ✓ Migrated {len(rows)} rows to table: {table_name}")
            
        except mysql.connector.Error as e:
            print(f"  ✗ Error migrating data for table {table_name}: {e}")
            self.mysql_conn.rollback()
        finally:
            sqlite_cursor.close()
            mysql_cursor.close()
    
    def migrate(self, drop_existing: bool = False):
        """
        Perform the complete migration.
        
        Args:
            drop_existing: If True, drop existing MySQL tables before migration
        """
        print("\n=== Starting SQLite to MySQL Migration ===\n")
        
        self.connect()
        
        # Get all tables from SQLite
        tables = self.get_sqlite_tables()
        print(f"Found {len(tables)} tables to migrate: {', '.join(tables)}\n")
        
        if not tables:
            print("No tables found in SQLite database.")
            self.close()
            return
        
        # Process each table
        for table_name in tables:
            print(f"Processing table: {table_name}")
            
            # Drop table if requested
            if drop_existing:
                cursor = self.mysql_conn.cursor()
                try:
                    cursor.execute(f"DROP TABLE IF EXISTS `{table_name}`;")
                    self.mysql_conn.commit()
                    print(f"  ✓ Dropped existing table: {table_name}")
                except mysql.connector.Error as e:
                    print(f"  ✗ Error dropping table {table_name}: {e}")
                finally:
                    cursor.close()
            
            # Get schema and create table
            schema = self.get_table_schema(table_name)
            self.create_mysql_table(table_name, schema)
            
            # Migrate data
            self.migrate_table_data(table_name)
            print()
        
        self.close()
        print("=== Migration Complete ===\n")


def main():
    """Main entry point for the script."""
    parser = argparse.ArgumentParser(
        description='Migrate SQLite3 database to MySQL/MariaDB',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s -s database.db -H localhost -u root -p password -d mydb
  %(prog)s -s database.db -H localhost -u root -p password -d mydb --drop
  %(prog)s -s database.db -H localhost -u root -P 3307 -d mydb

Note: This script has been tested with UptimeKuma migration (v2 onwards).
"""
    )
    
    parser.add_argument('-s', '--sqlite', required=True,
                        help='Path to SQLite database file')
    parser.add_argument('-H', '--host', default='localhost',
                        help='MySQL host (default: localhost)')
    parser.add_argument('-P', '--port', type=int, default=3306,
                        help='MySQL port (default: 3306)')
    parser.add_argument('-u', '--user', required=True,
                        help='MySQL username')
    parser.add_argument('-p', '--password', required=True,
                        help='MySQL password')
    parser.add_argument('-d', '--database', required=True,
                        help='MySQL database name')
    parser.add_argument('--drop', action='store_true',
                        help='Drop existing tables before migration')
    
    args = parser.parse_args()
    
    # Prepare MySQL configuration
    mysql_config = {
        'host': args.host,
        'port': args.port,
        'user': args.user,
        'password': args.password,
        'database': args.database
    }
    
    # Create migrator and run migration
    migrator = SQLiteToMySQLMigrator(args.sqlite, mysql_config)
    migrator.migrate(drop_existing=args.drop)


if __name__ == '__main__':
    main()
