#!/usr/bin/env python3
"""
Test specifically for Collation handling using Mocking.
"""

import sys
import os
import unittest
from unittest.mock import MagicMock, patch

# Add parent directory to path to import migrate
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from migrate import migrate_sqlite_to_mysql
import sqlite3

class TestCollation(unittest.TestCase):
    def setUp(self):
        # Create a simple SQLite DB
        self.sqlite_db = 'test_collation.db'
        if os.path.exists(self.sqlite_db):
            os.remove(self.sqlite_db)
            
        conn = sqlite3.connect(self.sqlite_db)
        cursor = conn.cursor()
        cursor.execute("CREATE TABLE test_col (id INTEGER PRIMARY KEY, val TEXT)")
        cursor.execute("INSERT INTO test_col VALUES (1, 'abc')")
        conn.commit()
        conn.close()

        self.mysql_config = {
            'host': 'localhost',
            'user': 'root',
            'password': '',
            'database': 'test_db',
            # We will set 'collation' in the test methods
        }

    def tearDown(self):
        if os.path.exists(self.sqlite_db):
            os.remove(self.sqlite_db)

    @patch('mysql.connector.connect')
    def test_custom_collation(self, mock_connect):
        # Setup the mock
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_connect.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor

        # Set specific collation
        target_collation = 'utf8mb4_uca1400_ai_ci'
        self.mysql_config['collation'] = target_collation
        
        migrate_sqlite_to_mysql(self.sqlite_db, self.mysql_config)

        # Check all execute calls to find the CREATE TABLE statement
        create_stmt_found = False
        for call in mock_cursor.execute.call_args_list:
            args, _ = call
            sql = args[0]
            if "CREATE TABLE IF NOT EXISTS `test_col`" in sql:
                if f"COLLATE={target_collation}" in sql:
                    create_stmt_found = True
        
        self.assertTrue(create_stmt_found, f"CREATE TABLE statement with COLLATE={target_collation} not found in executed queries.")

    @patch('mysql.connector.connect')
    def test_default_collation(self, mock_connect):
        # Setup the mock
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_connect.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor

        # Remove collation key (default behavior)
        if 'collation' in self.mysql_config:
            del self.mysql_config['collation']
            
        migrate_sqlite_to_mysql(self.sqlite_db, self.mysql_config)

        # Check all execute calls to find the CREATE TABLE statement
        create_stmt_found = False
        expected_default = 'utf8mb4_unicode_ci'
        
        for call in mock_cursor.execute.call_args_list:
            args, _ = call
            sql = args[0]
            if "CREATE TABLE IF NOT EXISTS `test_col`" in sql:
                if f"COLLATE={expected_default}" in sql:
                    create_stmt_found = True
        
        self.assertTrue(create_stmt_found, f"CREATE TABLE statement with default COLLATE={expected_default} not found.")

if __name__ == '__main__':
    unittest.main()
