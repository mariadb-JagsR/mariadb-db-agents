-- Enable Performance Schema in MariaDB/MySQL
-- Note: Performance Schema may require server restart in some configurations

-- 1. Check current status
SELECT @@performance_schema;

-- 2. Enable Performance Schema (if not already enabled)
-- This requires SUPER privilege and may require server restart
SET GLOBAL performance_schema = ON;

-- 3. Verify it's enabled
SELECT @@performance_schema;

-- 4. Check if Performance Schema tables are accessible
SELECT COUNT(*) FROM performance_schema.threads;

-- 5. Enable specific Performance Schema consumers (if needed)
-- These control what data is collected
UPDATE performance_schema.setup_consumers 
SET ENABLED = 'YES' 
WHERE NAME IN (
    'events_statements_current',
    'events_statements_history',
    'events_statements_history_long',
    'events_statements_summary_by_digest',
    'events_waits_current',
    'events_waits_history',
    'events_waits_history_long'
);

-- 6. Enable specific Performance Schema instruments (if needed)
-- These control what events are monitored
UPDATE performance_schema.setup_instruments 
SET ENABLED = 'YES', TIMED = 'YES'
WHERE NAME LIKE 'statement/%' OR NAME LIKE 'wait/%';

-- 7. Verify consumers are enabled
SELECT * FROM performance_schema.setup_consumers WHERE ENABLED = 'YES';

-- 8. Verify instruments are enabled
SELECT COUNT(*) as enabled_instruments 
FROM performance_schema.setup_instruments 
WHERE ENABLED = 'YES' AND TIMED = 'YES';

-- Note: If performance_schema variable is read-only, you may need to:
-- 1. Add to my.cnf / my.ini:
--    [mysqld]
--    performance_schema = ON
-- 2. Restart the MySQL/MariaDB server

