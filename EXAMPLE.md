# Example: Migrating an SQLite Database to MySQL

This example demonstrates how to use the `sqlite3tomysql.py` script to migrate a SQLite database to MySQL.

## Prerequisites

1. Install the required dependency:
```bash
pip install mysql-connector-python
```

2. Ensure you have:
   - A SQLite database file (e.g., `mydata.db`)
   - Access to a MySQL/MariaDB server
   - An existing MySQL database to migrate into

## Step-by-Step Guide

### 1. Prepare Your MySQL Database

First, create a target database in MySQL (if it doesn't exist):

```bash
mysql -u root -p
```

```sql
CREATE DATABASE mydatabase CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
EXIT;
```

### 2. Basic Migration

Migrate your SQLite database to MySQL:

```bash
python sqlite3tomysql.py \
  -s mydata.db \
  -H localhost \
  -u root \
  -p mypassword \
  -d mydatabase
```

This will:
- Connect to SQLite database `mydata.db`
- Connect to MySQL server at `localhost`
- Use MySQL user `root` with password `mypassword`
- Migrate all tables to database `mydatabase`

### 3. Migration with Custom Port

If your MySQL server runs on a non-standard port:

```bash
python sqlite3tomysql.py \
  -s mydata.db \
  -H localhost \
  -P 3307 \
  -u root \
  -p mypassword \
  -d mydatabase
```

### 4. Migration with Drop Option

If you want to recreate tables (drop existing ones first):

```bash
python sqlite3tomysql.py \
  -s mydata.db \
  -H localhost \
  -u root \
  -p mypassword \
  -d mydatabase \
  --drop
```

**Warning**: This will delete existing tables before migration!

### 5. Remote MySQL Server

Migrate to a remote MySQL server:

```bash
python sqlite3tomysql.py \
  -s mydata.db \
  -H mysql.example.com \
  -u myuser \
  -p mypassword \
  -d mydatabase
```

## Example Output

```
=== Starting SQLite to MySQL Migration ===

✓ Connected to SQLite database: mydata.db
✓ Connected to MySQL server
Found 2 tables to migrate: users, products

Processing table: users
  ✓ Created table: users
  ✓ Migrated 150 rows to table: users

Processing table: products
  ✓ Created table: products
  ✓ Migrated 42 rows to table: products

✓ Closed SQLite connection
✓ Closed MySQL connection

=== Migration Complete ===
```

## UptimeKuma Example

This script has been specifically tested with UptimeKuma (v2 onwards):

```bash
# Migrate UptimeKuma SQLite database to MySQL
python sqlite3tomysql.py \
  -s /path/to/uptime-kuma/data/kuma.db \
  -H localhost \
  -u uptimekuma \
  -p your_password \
  -d uptimekuma
```

## Troubleshooting

### Connection Errors

If you get connection errors:
- Verify MySQL server is running
- Check MySQL credentials are correct
- Ensure the target database exists
- Verify firewall rules allow the connection

### Permission Errors

If you get permission errors:
- Ensure MySQL user has CREATE, INSERT privileges
- Grant necessary permissions:
  ```sql
  GRANT ALL PRIVILEGES ON mydatabase.* TO 'myuser'@'localhost';
  FLUSH PRIVILEGES;
  ```

### Table Already Exists

If tables already exist:
- Use the `--drop` flag to recreate them
- Or manually drop tables in MySQL first

## Best Practices

1. **Backup First**: Always backup your SQLite database before migration
2. **Test Migration**: Test on a non-production database first
3. **Verify Data**: After migration, verify the data integrity
4. **Check Constraints**: Review primary keys and constraints after migration
5. **Performance**: For large databases, the migration may take time

## Verification

After migration, verify your data:

```bash
mysql -u root -p mydatabase
```

```sql
SHOW TABLES;
SELECT COUNT(*) FROM users;
SELECT * FROM users LIMIT 5;
```

Compare with SQLite:

```bash
sqlite3 mydata.db
```

```sql
.tables
SELECT COUNT(*) FROM users;
SELECT * FROM users LIMIT 5;
```
