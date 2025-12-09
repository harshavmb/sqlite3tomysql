#!/usr/bin/env python3
"""
Creates a test SQLite database (kuma.db) with various edge cases for migration testing.
This includes:
- Reserved MySQL keywords as table/column names
- Various data types (INT, TEXT, BLOB, REAL, DATETIME, TIME, BOOLEAN)
- PRIMARY KEY with AUTO_INCREMENT
- UNIQUE constraints (single and composite)
- DEFAULT values (including CURRENT_TIMESTAMP)
- NULL and NOT NULL constraints
- Large VARCHAR fields
- Special characters in data
- Timestamp conversions
"""

import sqlite3
from datetime import datetime
import os

def create_test_database(db_path='kuma.db'):
    # Remove existing database if it exists
    if os.path.exists(db_path):
        os.remove(db_path)
        print(f"Removed existing {db_path}")
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    print(f"Creating test database: {db_path}")
    
    # Table 1: Monitor table (typical Uptime Kuma structure)
    cursor.execute("""
        CREATE TABLE monitor (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name VARCHAR(150) NOT NULL,
            active BOOLEAN DEFAULT 1 NOT NULL,
            type VARCHAR(20),
            url TEXT,
            method VARCHAR(10) DEFAULT 'GET',
            interval INTEGER DEFAULT 60,
            retryInterval INTEGER DEFAULT 60,
            maxretries INTEGER DEFAULT 0,
            weight INTEGER DEFAULT 2000,
            timeout INTEGER DEFAULT 48,
            created_date DATETIME DEFAULT CURRENT_TIMESTAMP,
            keyword TEXT
        )
    """)
    print("Created table: monitor")
    
    # Insert test data for monitor
    cursor.execute("""
        INSERT INTO monitor (name, active, type, url, method, interval, keyword)
        VALUES 
            ('Google DNS', 1, 'ping', '8.8.8.8', 'GET', 60, NULL),
            ('Test Website', 1, 'http', 'https://example.com', 'GET', 120, 'Example Domain'),
            ('API Endpoint', 0, 'http', 'https://api.test.com/health', 'POST', 300, 'ok')
    """)
    
    # Table 2: Heartbeat table (large dataset simulation)
    cursor.execute("""
        CREATE TABLE heartbeat (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            monitor_id INTEGER NOT NULL,
            status TINYINT DEFAULT 0,
            msg TEXT,
            time DATETIME DEFAULT CURRENT_TIMESTAMP,
            ping REAL,
            important BOOLEAN DEFAULT 0
        )
    """)
    print("Created table: heartbeat")
    
    # Insert test data for heartbeat
    for i in range(50):
        cursor.execute("""
            INSERT INTO heartbeat (monitor_id, status, msg, ping, important)
            VALUES (?, ?, ?, ?, ?)
        """, (
            (i % 3) + 1,  # Rotate between monitor IDs 1-3
            1 if i % 4 != 0 else 0,  # Mostly up, some down
            f'Test message {i} with special chars: <>&"\'',
            round(10.5 + (i % 20), 2),  # Ping times
            1 if i % 10 == 0 else 0  # Some important
        ))
    
    # Table 3: API Key table (UNIQUE constraints, VARCHAR index limit edge case)
    cursor.execute("""
        CREATE TABLE api_key (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            client_name VARCHAR(191) NOT NULL UNIQUE,
            key_hash VARCHAR(191) NOT NULL UNIQUE,
            permissions TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            is_active BOOLEAN DEFAULT 1
        )
    """)
    print("Created table: api_key")
    
    # Insert test data for api_key
    cursor.execute("""
        INSERT INTO api_key (client_name, key_hash, permissions)
        VALUES 
            ('admin-client', 'hash_admin_12345', 'read,write,delete'),
            ('readonly-client', 'hash_readonly_67890', 'read'),
            ('test-client', 'hash_test_abcdef', 'read,write')
    """)
    
    # Table 4: Maintenance table (TIME data type edge case)
    cursor.execute("""
        CREATE TABLE maintenance (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title VARCHAR(150) NOT NULL,
            description TEXT,
            strategy VARCHAR(50) DEFAULT 'single',
            active BOOLEAN DEFAULT 1,
            start_date DATE,
            end_date DATE,
            start_time TIME,
            end_time TIME,
            weekdays TEXT,
            days_of_month TEXT
        )
    """)
    print("Created table: maintenance")
    
    # Insert test data for maintenance
    cursor.execute("""
        INSERT INTO maintenance (title, description, strategy, start_date, end_date, start_time, end_time, weekdays)
        VALUES 
            ('Weekly Backup', 'System backup window', 'recurring', '2024-01-01', '2024-12-31', '02:00:00', '04:00:00', 'Sunday'),
            ('System Upgrade', 'Major system upgrade', 'single', '2024-06-15', '2024-06-15', '22:00:00', '23:59:59', NULL)
    """)
    
    # Table 5: Reserved keyword table (tests MySQL reserved word handling)
    cursor.execute("""
        CREATE TABLE `group` (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name VARCHAR(255) NOT NULL,
            weight INTEGER DEFAULT 1000
        )
    """)
    print("Created table: group (reserved keyword)")
    
    cursor.execute("""
        INSERT INTO `group` (name, weight) VALUES ('Server Group 1', 1000), ('Server Group 2', 2000)
    """)
    
    # Table 6: knex_migrations table (timestamp conversion edge case)
    cursor.execute("""
        CREATE TABLE knex_migrations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name VARCHAR(255),
            batch INTEGER,
            migration_time BIGINT
        )
    """)
    print("Created table: knex_migrations")
    
    # Insert with Unix timestamps (milliseconds)
    current_timestamp_ms = int(datetime.now().timestamp() * 1000)
    cursor.execute("""
        INSERT INTO knex_migrations (name, batch, migration_time)
        VALUES 
            ('20231201_create_monitor.js', 1, ?),
            ('20231202_create_heartbeat.js', 1, ?),
            ('20231203_create_api_key.js', 2, ?)
    """, (current_timestamp_ms - 86400000, current_timestamp_ms - 43200000, current_timestamp_ms))
    
    # Table 7: Tag table (TEXT/LONGTEXT edge case)
    cursor.execute("""
        CREATE TABLE tag (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name VARCHAR(255) NOT NULL UNIQUE,
            color VARCHAR(10),
            description TEXT
        )
    """)
    print("Created table: tag")
    
    cursor.execute("""
        INSERT INTO tag (name, color, description)
        VALUES 
            ('production', '#FF0000', 'Production environment monitors'),
            ('staging', '#00FF00', 'Staging environment monitors'),
            ('development', '#0000FF', 'Development environment with very long description that might test TEXT field limits and ensure proper migration handling')
    """)
    
    # Table 8: Notification table (JSON-like TEXT data)
    cursor.execute("""
        CREATE TABLE notification (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name VARCHAR(255),
            config TEXT,
            active BOOLEAN DEFAULT 1,
            user_id INTEGER,
            is_default BOOLEAN DEFAULT 0
        )
    """)
    print("Created table: notification")
    
    cursor.execute("""
        INSERT INTO notification (name, config, active, user_id)
        VALUES 
            ('Email Alert', '{"type":"email","to":"admin@example.com","subject":"Alert"}', 1, 1),
            ('Slack Webhook', '{"type":"slack","url":"https://hooks.slack.com/test","channel":"#alerts"}', 1, 1),
            ('Discord', '{"type":"discord","webhookUrl":"https://discord.com/api/webhooks/test"}', 0, 2)
    """)
    
    # Table 9: Status page table (BLOB edge case - storing binary data)
    cursor.execute("""
        CREATE TABLE status_page (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            slug VARCHAR(255) NOT NULL UNIQUE,
            title VARCHAR(255) NOT NULL,
            description TEXT,
            icon BLOB,
            theme VARCHAR(50) DEFAULT 'light',
            published BOOLEAN DEFAULT 1,
            show_tags BOOLEAN DEFAULT 0,
            domain_name_list TEXT
        )
    """)
    print("Created table: status_page")
    
    # Insert with binary data
    cursor.execute("""
        INSERT INTO status_page (slug, title, description, icon, theme)
        VALUES 
            ('main', 'Main Status Page', 'Public status page', ?, 'light'),
            ('internal', 'Internal Status', 'Internal monitoring dashboard', NULL, 'dark')
    """, (b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR',))  # Fake PNG header bytes
    
    # Table 10: Edge case numeric types
    cursor.execute("""
        CREATE TABLE metrics (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            metric_name VARCHAR(100) NOT NULL,
            tiny_value TINYINT DEFAULT 0,
            small_value SMALLINT DEFAULT 0,
            medium_value MEDIUMINT DEFAULT 0,
            big_value BIGINT DEFAULT 0,
            decimal_value DECIMAL(10,2) DEFAULT 0.00,
            float_value FLOAT DEFAULT 0.0,
            double_value DOUBLE DEFAULT 0.0
        )
    """)
    print("Created table: metrics")
    
    cursor.execute("""
        INSERT INTO metrics (metric_name, tiny_value, small_value, medium_value, big_value, decimal_value, float_value, double_value)
        VALUES 
            ('cpu_usage', 85, 1024, 65536, 9223372036854775807, 99.99, 3.14159, 2.718281828),
            ('memory_usage', 127, 32767, 8388607, 1234567890123456, 12345.67, 1.414, 1.732050808),
            ('disk_usage', -128, -32768, -8388608, -9223372036854775808, -999.99, -2.71, -3.141592654)
    """)
    
    # Commit and close
    conn.commit()
    conn.close()
    
    print(f"\n✅ Test database created successfully: {db_path}")
    print("\nDatabase statistics:")
    
    # Reopen to show statistics
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = cursor.fetchall()
    
    print(f"Total tables: {len(tables)}")
    for table in tables:
        table_name = table[0]
        cursor.execute(f"SELECT COUNT(*) FROM `{table_name}`")
        count = cursor.fetchone()[0]
        print(f"  - {table_name}: {count} rows")
    
    conn.close()

if __name__ == "__main__":
    create_test_database()
    print("\n✅ Ready to run migration with: python migrate.py")
