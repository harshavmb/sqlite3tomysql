# sqlite3tomysql
Sqlite3 to mariadb migration script. In theory this could be applied for any sqlite -> MariaDB migration but it hasn't been tested. Nevertheless, it won't make changes to kuma.db, so you could run against target MariaDB & see if this script does the job. 

All credits to [Seamlessly Migrating SQLite Databases to MySQL: A Comprehensive Python Guide](https://medium.com/@gadallah.hatem/seamlessly-migrating-sqlite-databases-to-mysql-a-comprehensive-python-guide-f8776f50e356).

## How to execute the script?

### Prerequisites

Before running the migration script, ensure you have the following setup:

1. **Python Environment**
   - Python 3.6 or higher installed
   - Install required Python package:
     ```bash
     pip install mysql-connector-python
     ```

2. **MySQL/MariaDB Database Setup**
   - Create a database and user with appropriate privileges:
     ```sql
     CREATE DATABASE kuma CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
     CREATE USER 'kuma_user'@'localhost' IDENTIFIED BY 'your_secure_password';
     GRANT ALL PRIVILEGES ON kuma.* TO 'kuma_user'@'localhost';
     FLUSH PRIVILEGES;
     ```

3. **Configure Script Variables**
   
   Edit the variables at the end of `migrate.py` file:
   
   ```python
   # Update SQLite database file path
   sqlite_database_file = 'data/kuma.db'  # Path to your SQLite database
   
   # Update MySQL connection configuration
   mysql_connection_config = {
       'host': 'localhost',           # MySQL server host
       'user': 'kuma_user',          # Database user
       'password': 'your_secure_password',  # User password
       'database': 'kuma'            # Target database name
   }
   ```

### Script Features

The migration script provides comprehensive SQLite to MySQL/MariaDB migration with the following capabilities:

- **Smart Type Mapping**: Automatically converts SQLite data types to appropriate MySQL equivalents
- **Reserved Word Handling**: Escapes MySQL reserved keywords (like `group`, `order`, `key`) with backticks
- **Index Compatibility**: Handles MySQL's 767-byte index limit by adjusting VARCHAR lengths for indexed columns
- **Foreign Key Management**: Temporarily disables foreign key checks during migration
- **Batch Processing**: Processes data in batches of 1000 rows for better performance
- **Error Recovery**: Uses `INSERT IGNORE` to skip duplicate key errors and continue processing
- **Timestamp Conversion**: Converts Unix timestamps to MySQL DATETIME format (especially for `knex_migrations` table)
- **Auto-increment Handling**: Properly maps SQLite INTEGER PRIMARY KEY to MySQL AUTO_INCREMENT

### Execution

Run the migration script:

```bash
python3 migrate.py
```

The script will prompt for confirmation before proceeding with the migration.

### Example Run Log

```
python3 migrate.py
WARNING: This will drop and recreate tables in MySQL database 'kuma'. Are you sure? (yes/no): yes
Connected to SQLite database: data/kuma.db
Connected to MySQL database: kuma
Disabled MySQL foreign key checks.
Found tables in SQLite: ['heartbeat', 'sqlite_sequence', 'user', 'notification', 'monitor_notification', 'tag', 'monitor_tag', 'setting', 'incident', 'group', 'monitor_group', 'notification_sent_history', 'docker_host', 'status_page', 'status_page_cname', 'maintenance', 'maintenance_status_page', 'monitor_maintenance', 'api_key', 'sqlite_stat1', 'knex_migrations', 'knex_migrations_lock', 'remote_browser', 'monitor_tls_info', 'proxy', 'monitor', 'stat_daily', 'stat_hourly', 'stat_minutely']

Processing table: `heartbeat`
Generated CREATE TABLE statement:
CREATE TABLE IF NOT EXISTS `heartbeat` (
    `id` INT UNSIGNED NOT NULL AUTO_INCREMENT,
    `important` TINYINT(1) NOT NULL DEFAULT 0,
    `monitor_id` INT UNSIGNED NOT NULL,
    `status` SMALLINT NOT NULL,
    `msg` LONGTEXT,
    `time` DATETIME NOT NULL,
    `ping` INT UNSIGNED,
    `duration` INT UNSIGNED NOT NULL DEFAULT 0,
    `down_count` INT UNSIGNED NOT NULL DEFAULT 0,
    `end_time` DATETIME DEFAULT NULL,
    `retries` INT UNSIGNED NOT NULL DEFAULT '0',
    PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
Table `heartbeat` created in MySQL.
Copying 15234 rows to `heartbeat` using: INSERT IGNORE INTO `heartbeat` (`id`,`important`,`monitor_id`,`status`,`msg`,`time`,`ping`,`duration`,`down_count`,`end_time`,`retries`) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
Successfully processed 16 batches out of 16 for table `heartbeat`
Data copied to `heartbeat`.

Processing table: `user`
Generated CREATE TABLE statement:
CREATE TABLE IF NOT EXISTS `user` (
    `id` INT UNSIGNED NOT NULL AUTO_INCREMENT,
    `username` VARCHAR(255) NOT NULL,
    `password` VARCHAR(255),
    `active` TINYINT(1) NOT NULL DEFAULT 1,
    `timezone` VARCHAR(150),
    `twofa_token` VARCHAR(32),
    `twofa_last_token` VARCHAR(32),
    `twofa_status` TINYINT(1) NOT NULL DEFAULT 0,
    PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
Table `user` created in MySQL.
Copying 1 rows to `user` using: INSERT IGNORE INTO `user` (`id`,`username`,`password`,`active`,`timezone`,`twofa_token`,`twofa_last_token`,`twofa_status`) VALUES (%s,%s,%s,%s,%s,%s,%s,%s)
Successfully processed 1 batches out of 1 for table `user`
Data copied to `user`.

...

Processing table: `stat_minutely`
Generated CREATE TABLE statement:
CREATE TABLE IF NOT EXISTS `stat_minutely` (
    `id` INT UNSIGNED NOT NULL AUTO_INCREMENT,
    `monitor_id` INT UNSIGNED NOT NULL,
    `timestamp` DATETIME NOT NULL,
    `ping` INT UNSIGNED,
    `up` INT UNSIGNED NOT NULL DEFAULT 0,
    `down` INT UNSIGNED NOT NULL DEFAULT 0,
    `ping_min` INT UNSIGNED DEFAULT 0,
    `ping_max` INT UNSIGNED DEFAULT 0,
    `extras` LONGTEXT,
    PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
Table `stat_minutely` created in MySQL.
Copying 42264 rows to `stat_minutely` using: INSERT IGNORE INTO `stat_minutely` (`id`,`monitor_id`,`timestamp`,`ping`,`up`,`down`,`ping_min`,`ping_max`,`extras`) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)
Successfully processed 43 batches out of 43 for table `stat_minutely`
Data copied to `stat_minutely`.

Foreign key checks re-enabled in MySQL.
Database connections closed.
```

## Uptime Kuma Migration Steps

For migrating Uptime Kuma from SQLite3 to MariaDB, follow these steps carefully:

### Prerequisites
⚠️ **Important**: First bump to V2 using SQLite3 database before migrating to MariaDB. This ensures migration scripts get executed and your schema will be in good shape. 

**Do not migrate from SQLite3 to MariaDB while going from v1 to v2** - this will not work as v2 is a major version and your v1 schema is not compatible with v2.

### Migration Process

1. **Shutdown Uptime Kuma**
   - Shutdown the Uptime Kuma node to ensure data consistency during migration

2. **Execute Migration Script**
   - Feed in MariaDB details in the Python script & execute it
   - Depending on the data volume (rows), migration may take a couple of minutes
   - Example: Migration with moderate data can take around 2 minutes

3. **Update Docker Configuration**
   - Bump docker image to 2.x version
   - Add MariaDB details to docker environment variables
   - Start the container

4. **Verification**
   - Boom, you have Uptime Kuma now running on MariaDB!

### Known Quirks Handled

This script handles several quirks specific to the migration:
- **Reserved Keywords**: Tables named `group` (MariaDB won't allow as it's a reserved keyword, but the script circumvents this with escape characters)
- Other edge cases are handled automatically by the script
