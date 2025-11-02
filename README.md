# sqlite3tomysql
Sqlite3 to mariadb migration script

## Uptime Kuma Migration Steps

For migrating Uptime Kuma from SQLite3 to MariaDB, follow these steps carefully:

### Prerequisites
⚠️ **Important**: First bump to V2 using sqlite3 database (migration scripts get executed & your schema will be in good shape). Don't migrate from sqlite3 -> mariadb from v1 -> v2 (not going to work as v2 is a major version, your v1 schema is not compatible with v2)

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
