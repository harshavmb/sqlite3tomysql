# sqlite3tomysql

A Python script to migrate SQLite3 databases to MySQL/MariaDB.

## Overview

This script provides a seamless way to migrate data from SQLite3 databases to MySQL or MariaDB. It automatically handles schema conversion and data transfer.

**Note**: While this may not work for all SQLite3 databases, it has been tested and verified to work with **UptimeKuma migration (v2 onwards)**.

## Features

- ✓ Automatic schema conversion from SQLite to MySQL
- ✓ Data type mapping between SQLite and MySQL
- ✓ Preserves table structure including primary keys and constraints
- ✓ Batch data migration with transaction support
- ✓ Optional table drop before migration
- ✓ UTF-8 support (utf8mb4)
- ✓ InnoDB engine for MySQL tables

## Requirements

- Python 3.6 or higher
- `mysql-connector-python` package

## Installation

1. Clone this repository:
```bash
git clone https://github.com/harshavmb/sqlite3tomysql.git
cd sqlite3tomysql
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

Or install the package directly:
```bash
pip install mysql-connector-python
```

## Usage

### Basic Usage

```bash
python sqlite3tomysql.py -s <sqlite_db_path> -H <mysql_host> -u <mysql_user> -p <mysql_password> -d <mysql_database>
```

### Examples

**Migrate a SQLite database to MySQL:**
```bash
python sqlite3tomysql.py -s database.db -H localhost -u root -p mypassword -d mydatabase
```

**Migrate with custom port:**
```bash
python sqlite3tomysql.py -s database.db -H localhost -P 3307 -u root -p mypassword -d mydatabase
```

**Drop existing tables before migration:**
```bash
python sqlite3tomysql.py -s database.db -H localhost -u root -p mypassword -d mydatabase --drop
```

### Command Line Options

| Option | Short | Description | Required | Default |
|--------|-------|-------------|----------|---------|
| `--sqlite` | `-s` | Path to SQLite database file | Yes | - |
| `--host` | `-H` | MySQL/MariaDB host | No | localhost |
| `--port` | `-P` | MySQL/MariaDB port | No | 3306 |
| `--user` | `-u` | MySQL/MariaDB username | Yes | - |
| `--password` | `-p` | MySQL/MariaDB password | Yes | - |
| `--database` | `-d` | MySQL/MariaDB database name | Yes | - |
| `--drop` | - | Drop existing tables before migration | No | False |

## How It Works

1. **Connection**: Establishes connections to both SQLite and MySQL databases
2. **Schema Discovery**: Reads table structures from the SQLite database
3. **Type Mapping**: Converts SQLite data types to compatible MySQL types
4. **Table Creation**: Creates tables in MySQL with appropriate schema
5. **Data Migration**: Transfers all data from SQLite to MySQL
6. **Cleanup**: Closes all database connections

## Data Type Mapping

The script automatically maps SQLite data types to MySQL equivalents:

| SQLite Type | MySQL Type |
|-------------|------------|
| INTEGER | INT |
| TEXT | TEXT |
| REAL | DOUBLE |
| BLOB | BLOB |
| NUMERIC | NUMERIC |
| VARCHAR | VARCHAR |
| DATETIME | DATETIME |
| BOOLEAN | TINYINT(1) |
| BIGINT | BIGINT |

## Limitations

- This script may not work perfectly with all SQLite databases due to differences in database engines
- Complex constraints and triggers may need manual adjustment
- Foreign key relationships are preserved in schema but may need verification
- Custom SQLite features (like virtual tables) are not supported

## Tested With

- ✓ **UptimeKuma** (v2 onwards)

## Acknowledgments

This script is based on the approach described in the article:
[Seamlessly Migrating SQLite Databases to MySQL: A Comprehensive Python Guide](https://medium.com/@gadallah.hatem/seamlessly-migrating-sqlite-databases-to-mysql-a-comprehensive-python-guide-f8776f50e356) by Gadallah Hatem.

## License

See [LICENSE](LICENSE) file for details.

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## Support

If you encounter any issues or have questions, please open an issue on GitHub.
