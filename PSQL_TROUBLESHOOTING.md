# PostgreSQL Troubleshooting Commands

## Connection & Status

```bash
# Check if PostgreSQL is running
sudo systemctl status postgresql

# List all databases
psql -l

# Connect to a specific database
psql -d bible_teacher

# Connect as a specific user
psql -U postgres -d bible_teacher

# Connect with full connection string
psql "host=localhost port=5432 dbname=bible_teacher user=postgres password=yourpassword"
```

## Inside psql Shell

```sql
-- List all databases
\l

-- Connect to a database
\c bible_teacher

-- List all tables
\dt

-- List all tables (including schemas)
\dt *

-- Describe a table
\d table_name

-- List all users/roles
\du

-- Show current user
SELECT current_user;

-- Show current database
SELECT current_database();
```

## Connection & Activity

```sql
-- Show active connections
SELECT * FROM pg_stat_activity;

-- Show connections to a specific database
SELECT * FROM pg_stat_activity WHERE datname = 'bible_teacher';

-- Count active connections
SELECT count(*) FROM pg_stat_activity;

-- Show blocked queries
SELECT * FROM pg_locks WHERE NOT granted;

-- Terminate a specific connection (use pid from pg_stat_activity)
SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE pid = 12345;

-- Terminate all connections to a database
SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = 'bible_teacher';
```

## Database Size & Tables

```sql
-- Show database size
SELECT pg_size_pretty(pg_database_size('bible_teacher'));

-- Show size of all databases
SELECT datname, pg_size_pretty(pg_database_size(datname)) FROM pg_database;

-- Show table sizes (largest first)
SELECT schemaname, relname, pg_size_pretty(pg_total_relation_size(relid))
FROM pg_catalog.pg_statio_user_tables
ORDER BY pg_total_relation_size(relid) DESC;

-- Show size of a specific table
SELECT pg_size_pretty(pg_total_relation_size('table_name'));

-- Show table row counts (approximate)
SELECT schemaname, relname, n_live_tup FROM pg_stat_user_tables;
```

## Locks & Blocking

```sql
-- Show current locks
SELECT * FROM pg_locks;

-- Show blocking queries
SELECT blocked_locks.pid AS blocked_pid,
       blocked_activity.usename AS blocked_user,
       blocking_locks.pid AS blocking_pid,
       blocking_activity.usename AS blocking_user,
       blocked_activity.query AS blocked_statement,
       blocking_activity.query AS blocking_statement
FROM pg_catalog.pg_locks blocked_locks
JOIN pg_catalog.pg_stat_activity blocked_activity ON blocked_activity.pid = blocked_locks.pid
JOIN pg_catalog.pg_locks blocking_locks ON blocking_locks.locktype = blocked_locks.locktype
  AND blocking_locks.relation = blocked_locks.relation
  AND blocking_locks.pid != blocked_locks.pid
JOIN pg_catalog.pg_stat_activity blocking_activity ON blocking_activity.pid = blocking_locks.pid
WHERE NOT blocked_locks.granted;
```

## Slow Queries & Performance

```sql
-- Show slow queries by total execution time
SELECT query, calls, total_exec_time, mean_exec_time
FROM pg_stat_statements
ORDER BY total_exec_time DESC
LIMIT 10;

-- Reset query statistics (requires pg_stat_statements extension)
SELECT pg_stat_statements_reset();

-- Show index usage
SELECT schemaname, relname, seq_scan, seq_tup_read, idx_scan, idx_tup_fetch
FROM pg_stat_user_tables
ORDER BY seq_scan DESC;

-- Show unused indexes
SELECT schemaname, relname, indexrelname, idx_scan
FROM pg_stat_user_indexes
WHERE idx_scan = 0;
```

## Replication (if applicable)

```sql
-- Show replication status
SELECT * FROM pg_stat_replication;

-- Show replication lag
SELECT client_addr, state, sent_lsn, write_lsn, flush_lsn, replay_lsn
FROM pg_stat_replication;
```

## Logs & Configuration

```bash
# View PostgreSQL logs
sudo tail -f /var/log/postgresql/postgresql-*.log

# Show PostgreSQL configuration file location
SHOW config_file;

# Show data directory
SHOW data_directory;

# Show all configuration settings
SHOW ALL;
```

## Common Fixes

```bash
# Restart PostgreSQL
sudo systemctl restart postgresql

# Reload configuration without restart
sudo systemctl reload postgresql

# Create a database backup
pg_dump -U postgres -d bible_teacher > backup.sql

# Restore from backup
psql -U postgres -d bible_teacher < backup.sql

# Drop and recreate a database
DROP DATABASE IF EXISTS bible_teacher;
CREATE DATABASE bible_teacher OWNER postgres;
```

## Django-Specific

```bash
# Verify Django database connection
python manage.py dbshell

# Check Django migrations status
python manage.py showmigrations

# Run migrations
python manage.py migrate

# Create a Django admin superuser
python manage.py createsuperuser
```
