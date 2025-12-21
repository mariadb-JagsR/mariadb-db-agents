# src/common/db_client.py
from __future__ import annotations

import logging
from typing import Any, List, Dict

import mysql.connector
from mysql.connector import Error as MySQLError

from .config import DBConfig

logger = logging.getLogger(__name__)


def is_read_only_sql(sql: str) -> bool:
    """
    Very conservative read-only check. You can make this smarter,
    but for safety we reject any statement that *looks* like it may be DML/DDL.
    """
    stripped = sql.strip().lower()
    forbidden_prefixes = (
        "insert", "update", "delete", "replace", "alter",
        "create", "drop", "truncate", "rename", "set ",
        "grant", "revoke", "flush", "kill",
    )
    return not any(stripped.startswith(pfx) for pfx in forbidden_prefixes)


def detect_table_database(sql: str, cfg: DBConfig) -> str | None:
    """
    Try to detect which database a table belongs to by checking if it exists.
    This is a fallback when SQL doesn't have explicit database.table syntax.
    
    Common tables we know about:
    - beer_reviews_flat -> beer_reviews
    - slow_log -> mysql
    """
    import re
    
    # Known table to database mappings
    known_tables = {
        'beer_reviews_flat': 'beer_reviews',
        'slow_log': 'mysql',
        'beer_reviews_small': 'beer_reviews',
    }
    
    # Extract table names from SQL - handle both database.table and just table
    # Pattern 1: Extract from database.table syntax (e.g., mysql.beer_reviews_flat -> beer_reviews_flat)
    db_table_pattern = r'(?:FROM|JOIN|UPDATE|INTO|TABLE)\s+`?(\w+)`?\.`?(\w+)`?'
    matches = re.finditer(db_table_pattern, sql, re.IGNORECASE)
    for match in matches:
        db_name = match.group(1).lower()
        table_name = match.group(2).lower()
        # If database is mysql but table is known to be in another DB, return that DB
        if db_name == 'mysql' and table_name in known_tables:
            return known_tables[table_name]
        # If table is known, return its database
        if table_name in known_tables:
            return known_tables[table_name]
    
    # Pattern 2: Extract table names without database prefix
    table_patterns = [
        r'FROM\s+(?!`?\w+`?\.)`?(\w+)`?(?:\s|$|,|WHERE|JOIN|LIMIT|ORDER|GROUP|HAVING)',  # FROM table (not db.table)
        r'JOIN\s+(?!`?\w+`?\.)`?(\w+)`?(?:\s|$|ON|WHERE|LIMIT|ORDER|GROUP|HAVING)',  # JOIN table (not db.table)
        r'UPDATE\s+(?!`?\w+`?\.)`?(\w+)`?(?:\s|$|SET)',  # UPDATE table (not db.table)
        r'INTO\s+(?!`?\w+`?\.)`?(\w+)`?(?:\s|$|\(|VALUES)',  # INTO table (not db.table)
        r'SHOW\s+(?:CREATE\s+TABLE|INDEX\s+FROM|COLUMNS\s+FROM)\s+(?!`?\w+`?\.)`?(\w+)`?(?:\s|$|FROM)',  # SHOW ... table (not db.table)
        r'TABLE\s+(?!`?\w+`?\.)`?(\w+)`?(?:\s|$|\(|SET|WHERE)',  # TABLE name (not db.table)
    ]
    
    for pattern in table_patterns:
        matches = re.finditer(pattern, sql, re.IGNORECASE)
        for match in matches:
            table_name = match.group(1).lower()
            if table_name in known_tables:
                return known_tables[table_name]
    
    return None


def extract_database_from_sql(sql: str) -> str | None:
    """
    Extract database name from SQL query if it's explicitly referenced.
    
    Examples:
    - "SELECT * FROM beer_reviews.beer_reviews_flat" -> "beer_reviews"
    - "SELECT * FROM mysql.slow_log" -> "mysql"
    - "SHOW TABLES FROM beer_reviews" -> "beer_reviews"
    - "SELECT * FROM beer_reviews_flat" -> None (no explicit database)
    """
    import re
    
    # Look for database.table pattern or SHOW TABLES FROM database
    # Pattern: database.table or `database`.`table`
    patterns = [
        (r'FROM\s+`?(\w+)`?\.', 'FROM db.'),  # FROM db.table (most common)
        (r'JOIN\s+`?(\w+)`?\.', 'JOIN db.'),  # JOIN db.table
        (r'SHOW\s+TABLES\s+FROM\s+`?(\w+)`?', 'SHOW TABLES FROM db'),  # SHOW TABLES FROM db (not SHOW INDEX FROM)
        (r'`?(\w+)`?\.`?\w+`?', 'db.table'),  # Generic db.table pattern (must have dot)
    ]
    
    # Keywords to skip (not databases)
    skip_keywords = {
        'select', 'from', 'join', 'where', 'order', 'group', 'having',
        'insert', 'update', 'delete', 'create', 'drop', 'alter', 'show',
        'tables', 'index', 'indexes', 'columns', 'variables'
    }
    
    for pattern, desc in patterns:
        matches = re.finditer(pattern, sql, re.IGNORECASE)
        for match in matches:
            db_name = match.group(1)
            # Skip common keywords that might match
            if db_name.lower() not in skip_keywords:
                return db_name
    
    return None


def run_readonly_query(
    sql: str,
    max_rows: int = 1000,
    timeout_seconds: int = 5,
    database: str | None = None,
) -> List[Dict[str, Any]]:
    """
    Run a read-only SQL query against a MariaDB instance.
    
    Database connection is configured via environment variables (DB_HOST, DB_PORT, DB_USER, DB_PASSWORD, DB_DATABASE).

    Args:
        sql: SQL query to execute
        max_rows: Maximum number of rows to return
        timeout_seconds: Connection timeout
        database: Optional database name to use. If not provided, will try to extract
                  from SQL (e.g., beer_reviews.table_name) or use default from config.
    """
    if not is_read_only_sql(sql):
        raise ValueError(f"Refusing to execute non read-only SQL: {sql[:80]}...")

    cfg = DBConfig.from_env()
    
    # Determine which database to use
    target_database = database
    
    # First, try to detect from table names (this catches beer_reviews_flat even without prefix)
    detected_table_db = detect_table_database(sql, cfg)
    
    if not target_database:
        # Try to extract from SQL (database.table syntax)
        target_database = extract_database_from_sql(sql)
    
    # CRITICAL FIX: If SQL has mysql.table_name but table_name is known to be in another DB,
    # override the database. This handles cases where agent incorrectly generates mysql.beer_reviews_flat
    if target_database and target_database.lower() == 'mysql':
        # Check if the table name suggests it's actually in a different database
        if detected_table_db and detected_table_db.lower() != 'mysql':
            logger.warning(
                f"SQL has 'mysql.' prefix but table is in '{detected_table_db}' database. "
                f"Overriding to use '{detected_table_db}' database."
            )
            target_database = detected_table_db
    
    # If still no database, use the detected table database
    if not target_database:
        target_database = detected_table_db
        if target_database:
            logger.debug(f"Detected database '{target_database}' from table name in SQL")
    
    # Default to config database if no database specified in query
    if not target_database:
        target_database = cfg.database
        logger.debug(f"Using default database '{target_database}' from config")
    
    logger.debug(f"Executing SQL in database '{target_database}': {sql[:100]}...")
    
    conn = None
    try:
        # Connect without specifying database first (to allow switching)
        conn = mysql.connector.connect(
            host=cfg.host,
            port=cfg.port,
            user=cfg.user,
            password=cfg.password,
            connection_timeout=timeout_seconds,
            ssl_disabled=True,  # Skip SSL for SkySQL connections
        )

        cursor = conn.cursor(dictionary=True)
        cursor.execute("SET SESSION TRANSACTION READ ONLY")
        
        # Switch to the target database
        cursor.execute(f"USE `{target_database}`")
        
        # Normalize SQL: remove database prefix if present since we've already switched
        # This handles cases where SQL has "database.table" but we're now in that database
        normalized_sql = sql
        if target_database:
            # Remove database prefix from table references
            import re
            # Pattern: database.table or `database`.`table`
            # Remove the target database prefix
            pattern = rf'`?{re.escape(target_database)}`?\.'
            normalized_sql = re.sub(pattern, '', sql, flags=re.IGNORECASE)
            
            # CRITICAL: Also remove mysql. prefix if we're switching to a different database
            # This handles the case where agent generates mysql.beer_reviews_flat incorrectly
            if target_database.lower() != 'mysql':
                # Remove mysql. prefix from table references (but keep mysql.slow_log queries)
                # Only remove if the table after mysql. is known to be in another database
                mysql_pattern = r'mysql\.`?(\w+)`?'
                matches = list(re.finditer(mysql_pattern, normalized_sql, re.IGNORECASE))
                for match in matches:
                    table_name = match.group(1).lower()
                    # Check if this table is known to be in a different database
                    if table_name in ['beer_reviews_flat', 'beer_reviews_small']:
                        # Remove the mysql. prefix
                        normalized_sql = re.sub(
                            rf'mysql\.`?{re.escape(match.group(1))}`?',
                            match.group(1),
                            normalized_sql,
                            flags=re.IGNORECASE
                        )
        
        logger.debug(f"Normalized SQL: {normalized_sql[:100]}...")
        cursor.execute(normalized_sql)

        rows = cursor.fetchmany(size=max_rows)
        return list(rows)

    except MySQLError as ex:
        logger.exception("Error running read-only query")
        raise RuntimeError(f"DB query failed: {ex}") from ex
    finally:
        if conn is not None and conn.is_connected():
            conn.close()


def tail_slow_log_file(
    path: str | None = None,
    max_bytes: int = 1_000_000,
    tail_lines: int = 5000,
) -> str:
    """
    Stub for reading the tail of the slow query log file.

    In a real MariaDB Cloud / SkySQL deployment, you would NOT read
    the filesystem from here. Instead:
      - Expose an internal API or log service that can return the
        last N bytes / lines of the slow query log.

    For now, raise an error so it's obvious this requires implementation.
    """
    raise NotImplementedError(
        "tail_slow_log_file is not implemented. "
        "Replace this with a call to your internal log API."
    )

