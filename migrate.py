import sqlite3
import mysql.connector
import re # For regular expressions to parse types
from datetime import datetime

# MySQL (not MariaDB) does not support DEFAULT values for these column types
# Reference: MySQL error 1101 - BLOB, TEXT, GEOMETRY or JSON column can't have a default value
MYSQL_NO_DEFAULT_TYPES = [
    "LONGTEXT", "TEXT", "MEDIUMTEXT", "TINYTEXT",
    "BLOB", "LONGBLOB", "MEDIUMBLOB", "TINYBLOB",
    "JSON", "GEOMETRY"
]

def detect_is_mariadb(mysql_cursor):
    """
    Detects whether the connected database is MariaDB or MySQL.
    Returns True if MariaDB, False if MySQL.
    """
    try:
        mysql_cursor.execute("SELECT VERSION()")
        version_string = mysql_cursor.fetchone()[0]
        # MariaDB version strings contain 'MariaDB' (case-insensitive)
        return 'mariadb' in version_string.lower()
    except (mysql.connector.Error, AttributeError) as e:
        print(f"Warning: Could not detect database type via mysql.connector: {e}. Assuming MySQL (stricter rules).")
        return False  # Default to MySQL (more restrictive) if detection fails

def should_skip_default_for_mysql(mysql_type, is_mariadb):
    """
    Determines if DEFAULT value should be skipped for a given MySQL column type.
    MySQL (not MariaDB) does not support DEFAULT values for certain types.
    
    Args:
        mysql_type: The MySQL column type (e.g., "LONGTEXT", "VARCHAR(255)")
        is_mariadb: Boolean indicating if target database is MariaDB
    
    Returns:
        True if DEFAULT should be skipped, False otherwise
    """
    # Extract the base type name without size/parameters (e.g., "VARCHAR(255)" -> "VARCHAR")
    base_type = mysql_type.split('(')[0].strip().upper()
    is_problematic_type = base_type in MYSQL_NO_DEFAULT_TYPES
    return is_problematic_type and not is_mariadb

def escape_mysql_reserved_words(table_name):
    """
    Escapes MySQL reserved words by wrapping them in backticks.
    """
    mysql_reserved_words = {
        'group', 'order', 'key', 'index', 'table', 'database', 'column',
        'primary', 'foreign', 'unique', 'check', 'constraint', 'references',
        'add', 'alter', 'create', 'drop', 'insert', 'update', 'delete',
        'select', 'from', 'where', 'join', 'inner', 'left', 'right',
        'union', 'distinct', 'having', 'limit', 'offset', 'desc', 'asc'
    }
    
    if table_name.lower() in mysql_reserved_words:
        return f"`{table_name}`"
    return f"`{table_name}`"  # Always use backticks for safety

def map_sqlite_to_mysql_type(sqlite_type_raw, is_primary_key=False, is_unique=False):
    """
    Maps SQLite data types to appropriate MySQL data types.
    `is_unique` is used to identify columns that will form part of a unique index.
    """
    sqlite_type = sqlite_type_raw.upper()

    if "INT" in sqlite_type:
        if "TINYINT" in sqlite_type: return "TINYINT"
        elif "SMALLINT" in sqlite_type: return "SMALLINT"
        elif "MEDIUMINT" in sqlite_type: return "MEDIUMINT"
        elif "BIGINT" in sqlite_type: return "BIGINT UNSIGNED"
        # Use UNSIGNED integers to match typical application frameworks like Laravel/Knex
        return "INT UNSIGNED"

    elif "CHAR" in sqlite_type or "CLOB" in sqlite_type or "TEXT" in sqlite_type:
        # For indexed VARCHAR/TEXT columns (primary keys or unique), we must consider the 767-byte limit.
        # Max VARCHAR(191) for utf8mb4 where 191 * 4 bytes = 764 bytes <= 767 bytes.
        max_varchar_len_for_index = 191
        
        # If it's a primary key or has a UNIQUE constraint, it's indexed.
        if is_primary_key or is_unique:
            print(f"Warning: Indexed text column '{sqlite_type_raw}' mapped to VARCHAR({max_varchar_len_for_index}) for index compatibility due to MySQL's 767-byte limit (on older versions/default configs). Ensure data fits.")
            return f"VARCHAR({max_varchar_len_for_index})"
        
        match = re.search(r'\((\d+)\)', sqlite_type_raw)
        if match:
            length = int(match.group(1))
            # For non-indexed, we can use a larger VARCHAR if needed, up to MySQL's limit (65535 bytes)
            # but usually 255 is sufficient for short strings.
            return f"VARCHAR({min(length, 255)})" # Cap at 255 for common cases, can be higher if needed and not indexed
        return "LONGTEXT" # Default to LONGTEXT for general TEXT data if no specific length or not indexed

    elif "BLOB" in sqlite_type:
        if is_primary_key or is_unique:
            print(f"Warning: Indexed BLOB column '{sqlite_type_raw}' mapped to VARBINARY(191) for index compatibility. Ensure data fits.")
            return "VARBINARY(191)"
        return "BLOB" # Or LONGBLOB

    elif "REAL" in sqlite_type or "FLOA" in sqlite_type or "DOUB" in sqlite_type:
        return "DOUBLE"
    elif "NUM" in sqlite_type or "DEC" in sqlite_type:
        return "DECIMAL(10,2)"
    elif "BOOL" in sqlite_type:
        return "TINYINT(1)"
    elif sqlite_type == "TIME":
        # Handle TIME type specifically - should remain TIME in MySQL
        # This fixes the issue where start_time/end_time in maintenance table
        # were incorrectly converted to DATETIME instead of TIME
        return "TIME"
    elif "DATE" in sqlite_type:
        # Handle DATE and DATETIME types - both map to DATETIME in MySQL
        return "DATETIME"
    else:
        print(f"Warning: Unknown SQLite type '{sqlite_type_raw}'. Defaulting to VARCHAR(255).")
        return "VARCHAR(255)"

def migrate_sqlite_to_mysql(sqlite_db_path, mysql_config):
    """
    Migrates a SQLite database to MySQL, including table schemas and data.
    """
    sqlite_conn = None
    mysql_conn = None
    sqlite_cursor = None
    mysql_cursor = None

    try:
        sqlite_conn = sqlite3.connect(sqlite_db_path)
        sqlite_cursor = sqlite_conn.cursor()
        print(f"Connected to SQLite database: {sqlite_db_path}")
    except sqlite3.Error as e:
        print(f"Error connecting to SQLite: {e}")
        return

    try:
        mysql_conn = mysql.connector.connect(**mysql_config)
        mysql_cursor = mysql_conn.cursor()
        print(f"Connected to MySQL database: {mysql_config['database']}")
        
        # Detect if target is MariaDB or MySQL
        is_mariadb = detect_is_mariadb(mysql_cursor)
        db_type = "MariaDB" if is_mariadb else "MySQL"
        print(f"Detected target database type: {db_type}")
    except mysql.connector.Error as e:
        print(f"Error connecting to MySQL: {e}")
        if sqlite_cursor: sqlite_cursor.close()
        if sqlite_conn: sqlite_conn.close()
        return

    try:
        mysql_cursor.execute("SET FOREIGN_KEY_CHECKS = 0;")
        mysql_conn.commit()
        print("Disabled MySQL foreign key checks.")
    except mysql.connector.Error as err:
        print(f"Error disabling foreign key checks: {err}")

    try:
        sqlite_cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = sqlite_cursor.fetchall()
        print(f"Found tables in SQLite: {[t[0] for t in tables]}")

        for table_name_tuple in tables:
            table_name = table_name_tuple[0]
            if table_name == 'sqlite_sequence':
                print(f"Skipping internal SQLite table: {table_name}")
                continue
            if table_name.startswith('sqlite_autoindex_'):
                print(f"Skipping internal SQLite autoindex table: {table_name}")
                continue

            print(f"\nProcessing table: `{table_name}`")
            
            # Escape reserved keywords
            escaped_table_name = escape_mysql_reserved_words(table_name)

            # Handle reserved keywords in SQLite queries too
            if table_name.lower() in {'group', 'order', 'key', 'index', 'table'}:
                sqlite_cursor.execute(f"PRAGMA table_info(`{table_name}`);")
            else:
                sqlite_cursor.execute(f"PRAGMA table_info({table_name});")
            columns = sqlite_cursor.fetchall()
            col_defs = []
            primary_keys = []
            unique_constraints = {} # Stores {col_name: unique_group_name} if composite unique

            # Determine primary keys and unique columns for accurate type mapping and constraint generation
            pk_col_names = {col[1] for col in columns if col[5] == 1} # col[5] is 'pk'
            
            # Additional logic: Check for UNIQUE constraints from sqlite_master (if relevant for other tables)
            # For simplicity for 'api_key' example, we'll assume UNIQUE means single-column unique index.
            # A more advanced script would parse CREATE TABLE statements from sqlite_master to find composite unique keys.
            
            # For this specific api_key case: client_name and key_hash are UNIQUE.
            # We'll treat columns with UNIQUE constraints as 'is_unique=True' for type mapping.
            # This is a simplification; a full parser would be needed for complex multi-column unique keys.
            # For now, if a column is explicitly marked UNIQUE in the SQLite DDL, this will handle it.
            # The provided api_key DDL indicates client_name and key_hash are UNIQUE.

            for col in columns:
                col_name = col[1]
                sqlite_type = col[2]
                not_null = col[3]
                default_value = col[4]
                pk = col[5]

                # Determine if column has a UNIQUE constraint.
                # This simple check is for single-column UNIQUE.
                # For complex migrations, parsing CREATE statement is better.
                is_unique_col = False
                # Handle reserved keywords in SQLite queries
                if table_name.lower() in {'group', 'order', 'key', 'index', 'table'}:
                    sqlite_cursor.execute(f"PRAGMA index_list(`{table_name}`);")
                else:
                    sqlite_cursor.execute(f"PRAGMA index_list('{table_name}');")
                indexes = sqlite_cursor.fetchall()
                for idx in indexes:
                    idx_name = idx[1]
                    is_unique_idx = idx[2] # 1 for unique, 0 for not
                    if is_unique_idx == 1:
                        sqlite_cursor.execute(f"PRAGMA index_info('{idx_name}');")
                        idx_cols = sqlite_cursor.fetchall()
                        if len(idx_cols) == 1 and idx_cols[0][2] == col_name: # Check if single column index and matches current column
                            is_unique_col = True
                            break # Found a unique index for this column

                mysql_type = map_sqlite_to_mysql_type(
                    sqlite_type, 
                    is_primary_key=(col_name in pk_col_names),
                    is_unique=is_unique_col # Pass is_unique flag
                )
                
                auto_increment = ""
                if pk == 1 and ("INT" in mysql_type or "BIGINT" in mysql_type):
                    auto_increment = " AUTO_INCREMENT"
                    if not_null == 0:
                        print(f"Warning: Primary key '{col_name}' in table '{table_name}' is NULLABLE in SQLite. MySQL AUTO_INCREMENT implies NOT NULL.")
                    not_null_sql = " NOT NULL"
                elif not_null == 1:
                    not_null_sql = " NOT NULL"
                else:
                    not_null_sql = ""

                # Check if this column type cannot have DEFAULT values on MySQL (but can on MariaDB)
                skip_default_for_type = should_skip_default_for_mysql(mysql_type, is_mariadb)
                
                default_sql = ""
                # Handle default values. Special case for created_at/updated_at to manage in app if needed.
                if default_value is not None and not skip_default_for_type:
                    # Fix for DATETIME('now') FUNCTION - convert SQLite syntax to MySQL
                    default_str = str(default_value).upper().replace('"', "'")
                    if ("DATETIME('NOW')" in default_str or default_str == "DATETIME('NOW')" or 
                        default_str == "'CURRENT_TIMESTAMP'" or default_str == "CURRENT_TIMESTAMP"):
                        # For older MySQL/MariaDB versions, use TIMESTAMP instead of DATETIME with CURRENT_TIMESTAMP
                        if mysql_type == "DATETIME":
                            mysql_type = "TIMESTAMP"
                        default_sql = " DEFAULT CURRENT_TIMESTAMP"
                    # Handle 'NULL' string defaults
                    elif str(default_value).upper() in ["'NULL'", "NULL"]:
                        default_sql = " DEFAULT NULL"
                    # Handle numeric defaults but check for TINYINT overflow
                    elif isinstance(default_value, (int, float)) or str(default_value).replace('.', '').replace('-', '').isdigit():
                        numeric_value = float(default_value)
                        # Check for TINYINT overflow (range is -128 to 127, or 0 to 255 for unsigned)
                        if "TINYINT" in mysql_type and (numeric_value > 127 or numeric_value < -128):
                            print(f"Warning: Default value {default_value} for TINYINT column '{col_name}' exceeds TINYINT range. Converting column to SMALLINT.")
                            mysql_type = mysql_type.replace("TINYINT", "SMALLINT")
                        default_sql = f" DEFAULT {default_value}"
                    # Specific handling for the 'api_key' table's timestamps if they need app management
                    elif table_name == 'api_key' and col_name in ['created_at', 'updated_at']:
                        # Skip default for 'created_at' as we'll populate it in INSERT
                        # 'updated_at' will get ON UPDATE CURRENT_TIMESTAMP, not a DEFAULT
                        pass
                    elif isinstance(default_value, str) and (
                        "TEXT" in mysql_type or "VARCHAR" in mysql_type or
                        "DATE" in mysql_type or "TIME" in mysql_type or "LONGTEXT" in mysql_type
                    ):
                        default_value_clean = default_value.strip("'\"")
                        default_sql = f" DEFAULT '{default_value_clean}'"
                    else:
                        default_sql = f" DEFAULT {default_value}"
                elif default_value is not None and skip_default_for_type:
                    # Skip DEFAULT for problematic types on MySQL
                    print(f"Info: Skipping DEFAULT value '{default_value}' for {mysql_type} column '{col_name}' on MySQL (not supported).")
                
                # Add ON UPDATE CURRENT_TIMESTAMP specifically for 'updated_at' column in api_key table
                on_update_clause = ""
                if table_name == 'api_key' and col_name == 'updated_at':
                    on_update_clause = " ON UPDATE CURRENT_TIMESTAMP"
                    # For very old MySQL, TIMESTAMP needs to be NOT NULL to use ON UPDATE CURRENT_TIMESTAMP,
                    # and often DEFAULT CURRENT_TIMESTAMP is implicit or needs to be explicitly first TIMESTAMP.
                    # We'll set it to NOT NULL for simplicity here.
                    if not_null_sql == "": # Ensure it's NOT NULL for ON UPDATE CURRENT_TIMESTAMP in older versions
                        not_null_sql = " NOT NULL"
                    if default_sql == "": # Add default for updated_at if not present for older versions
                        default_sql = " DEFAULT CURRENT_TIMESTAMP"


                col_defs.append(f"`{col_name}` {mysql_type}{not_null_sql}{default_sql}{auto_increment}{on_update_clause}".strip())
                if pk == 1:
                    primary_keys.append(f"`{col_name}`")
                
                # Add UNIQUE constraint if the column was found to be unique
                if is_unique_col and col_name not in pk_col_names: # Don't add UNIQUE if it's already PK (PK implies unique)
                    col_defs.append(f"UNIQUE (`{col_name}`)")


            if primary_keys:
                col_defs.append(f"PRIMARY KEY ({', '.join(primary_keys)})")

            # FIX for Python 3.11+ f-string backslash issue
            joined_col_defs = ',\n    '.join(col_defs)
            
            # For older MySQL versions, adding ROW_FORMAT=DYNAMIC if supported might solve index length issues.
            # However, reducing VARCHAR length is the more reliable cross-version solution.
            # If your MySQL version supports it, you could add: ROW_FORMAT=DYNAMIC
            # create_stmt = f"CREATE TABLE IF NOT EXISTS `{table_name}` (\n    {joined_col_defs}\n) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci ROW_FORMAT=DYNAMIC;"
            
            # The most compatible CREATE TABLE statement based on our troubleshooting
            create_stmt = f"CREATE TABLE IF NOT EXISTS {escaped_table_name} (\n    {joined_col_defs}\n) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;"

            print(f"Generated CREATE TABLE statement:\n{create_stmt}")

            try:
                mysql_cursor.execute(f"DROP TABLE IF EXISTS {escaped_table_name};")
                mysql_cursor.execute(create_stmt)
                print(f"Table `{table_name}` created in MySQL.")
            except mysql.connector.Error as err:
                print(f"Error creating table `{table_name}`: {err}")
                continue

            # Handle reserved keywords in SQLite SELECT queries
            if table_name.lower() in {'group', 'order', 'key', 'index', 'table'}:
                sqlite_cursor.execute(f"SELECT * FROM `{table_name}`")
            else:
                sqlite_cursor.execute(f"SELECT * FROM {table_name}")
            rows = sqlite_cursor.fetchall()
            if rows:
                # Get column names to construct a proper INSERT statement
                if table_name.lower() in {'group', 'order', 'key', 'index', 'table'}:
                    sqlite_cursor.execute(f"PRAGMA table_info(`{table_name}`);")
                else:
                    sqlite_cursor.execute(f"PRAGMA table_info({table_name});")
                original_col_names = [col[1] for col in sqlite_cursor.fetchall()]

                # Adjust original_col_names and data based on MySQL's schema changes
                # For api_key, if 'created_at' is managed by app, we need to pass a value.
                # If 'updated_at' is auto-updated ON UPDATE, we can omit it on INSERT,
                # but providing NOW() is also fine and explicit.

                processed_rows = []
                for row_data in rows:
                    new_row = list(row_data) # Convert tuple to list for modification
                    
                    # Handle timestamp conversion for knex_migrations table
                    if table_name == 'knex_migrations' and len(new_row) >= 4:
                        # Convert Unix timestamp to MySQL DATETIME format
                        migration_time = new_row[3]  # migration_time column
                        if migration_time and str(migration_time).isdigit():
                            # Convert from milliseconds to seconds if needed
                            timestamp_val = int(migration_time)
                            if timestamp_val > 4000000000:  # If > year 2096, likely milliseconds
                                timestamp_val = timestamp_val // 1000
                            
                            try:
                                dt = datetime.fromtimestamp(timestamp_val)
                                new_row[3] = dt.strftime('%Y-%m-%d %H:%M:%S')
                            except (ValueError, OSError) as e:
                                print(f"Warning: Could not convert timestamp {migration_time}: {e}")
                                new_row[3] = None
                    
                    # Assume original 'created_at' and 'updated_at' are the last two columns if they exist.
                    # This is a simplification; a robust solution would use original_col_names.
                    
                    processed_rows.append(tuple(new_row))

                placeholders = ','.join(['%s'] * len(original_col_names))
                # Use INSERT IGNORE to skip duplicate key errors and continue processing
                insert_stmt = f"INSERT IGNORE INTO {escaped_table_name} ({','.join(f'`{col}`' for col in original_col_names)}) VALUES ({placeholders})"
                print(f"Copying {len(rows)} rows to `{table_name}` using: {insert_stmt}")

                batch_size = 1000
                successful_batches = 0
                for i in range(0, len(processed_rows), batch_size):
                    batch = processed_rows[i:i + batch_size]
                    
                    try:
                        mysql_cursor.executemany(insert_stmt, batch)
                        mysql_conn.commit()
                        successful_batches += 1
                    except mysql.connector.Error as err:
                        print(f"Error inserting data into `{table_name}` (batch {i//batch_size}, starting row {i}): {err}")
                        mysql_conn.rollback()
                        # Continue with next batch instead of breaking
                        continue
                
                print(f"Successfully processed {successful_batches} batches out of {(len(processed_rows) + batch_size - 1) // batch_size} for table `{table_name}`")
                print(f"Data copied to `{table_name}`.")
            else:
                print(f"No data to copy for table `{table_name}`.")

    except Exception as e:
        print(f"An unexpected error occurred during migration: {e}")
        if mysql_conn:
            mysql_conn.rollback()

    finally:
        if mysql_cursor and mysql_conn:
            try:
                mysql_cursor.execute("SET FOREIGN_KEY_CHECKS = 1;")
                mysql_conn.commit()
                print("\nForeign key checks re-enabled in MySQL.")
            except mysql.connector.Error as err:
                print(f"Error re-enabling foreign key checks: {err}")

        if mysql_cursor:
            mysql_cursor.close()
        if mysql_conn:
            mysql_conn.close()
        if sqlite_cursor:
            sqlite_cursor.close()
        if sqlite_conn:
            sqlite_conn.close()
        print("Database connections closed.")


# --- Configuration ---
sqlite_database_file = 'kuma.db' ## database file of sqlite
mysql_connection_config = {
    'host': 'localhost', ## change to remote mysql host
    'user': 'mysqluser', ## database user
    'password': 'changeme', ### password
    'database': 'mysqldatabase' ## database name
}

# --- Run the migration ---
if __name__ == "__main__":
    confirm = input(f"WARNING: This will drop and recreate tables in MySQL database '{mysql_connection_config['database']}'. Are you sure? (yes/no): ").lower()
    if confirm == 'yes':
        migrate_sqlite_to_mysql(sqlite_database_file, mysql_connection_config)
    else:
        print("Migration cancelled by user.")
