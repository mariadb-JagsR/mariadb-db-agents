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
        # Determine SSL configuration based on host/environment
        # Some SkySQL instances require SSL with certificate verification
        connect_kwargs = {
            'host': cfg.host,
            'port': cfg.port,
            'user': cfg.user,
            'password': cfg.password,
            'connection_timeout': timeout_seconds,
        }
        
        if 'skysql.com' in cfg.host.lower():
            # SkySQL instances require SSL with certificate verification
            # mysql-connector-python will use SSL if server requires it
            # For explicit SSL with verification, we don't disable SSL
            # SSL verification is the default behavior when SSL is enabled
            # This matches --ssl-verify-server-cert behavior from mariadb CLI
            # Note: mysql-connector-python handles SSL automatically when server requires it
            pass  # Let connector handle SSL automatically (default behavior)
        else:
            # For local/other connections, SSL may not be required
            connect_kwargs['ssl_disabled'] = True
        
        conn = mysql.connector.connect(**connect_kwargs)

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


def extract_error_log_patterns(
    log_content: str,
    max_patterns: int = 20,
) -> List[Dict[str, Any]]:
    """
    Extract error patterns from MariaDB error log content.
    
    Groups similar errors together and counts occurrences to avoid sending
    huge logs to the LLM. Normalizes error messages by replacing:
    - Timestamps
    - Process IDs
    - Connection IDs
    - Specific table/database names (with placeholders)
    - Specific error codes (kept for categorization)
    
    Args:
        log_content: Raw error log content
        max_patterns: Maximum number of unique patterns to return (default: 20)
    
    Returns:
        List of dictionaries with:
        - pattern: Normalized error message pattern
        - count: Number of occurrences
        - severity: Inferred severity (ERROR, WARNING, INFO)
        - first_seen: First occurrence timestamp (if available)
        - last_seen: Last occurrence timestamp (if available)
        - sample_message: One example of the actual error message
    """
    import re
    from collections import defaultdict
    from datetime import datetime
    
    if not log_content.strip():
        return []
    
    lines = log_content.split('\n')
    patterns = defaultdict(lambda: {
        'count': 0,
        'severity': 'UNKNOWN',
        'first_seen': None,
        'last_seen': None,
        'sample_message': None,
    })
    
    # Common MariaDB error log patterns
    # Standard MariaDB timestamp: 2025-12-17 20:41:25
    timestamp_pattern = r'\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2}'
    # ISO timestamp (Kubernetes/Docker): 2025-12-17T20:41:23.711701291Z
    iso_timestamp_pattern = r'\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d+Z'
    # Kubernetes log prefix: 2025-12-17T20:41:23.711701291Z stdout F
    k8s_prefix_pattern = rf'{iso_timestamp_pattern}\s+(stdout|stderr)\s+[A-Z]\s+'
    
    pid_pattern = r'\[\d+\]'
    connection_id_pattern = r'\[0x[0-9a-fA-F]+\]'
    
    # Error severity patterns
    error_keywords = ['ERROR', 'FATAL', 'CRITICAL', 'PANIC']
    warning_keywords = ['WARNING', 'WARN']
    info_keywords = ['INFO', 'NOTE', 'Note']
    
    for line in lines:
        if not line.strip():
            continue
        
        # Extract timestamp if present (prefer MariaDB timestamp, fallback to ISO)
        timestamp_match = re.search(timestamp_pattern, line)
        if not timestamp_match:
            timestamp_match = re.search(iso_timestamp_pattern, line)
        timestamp = timestamp_match.group(0) if timestamp_match else None
        
        # Normalize the error message
        normalized = line
        
        # Remove Kubernetes/Docker log prefix (ISO timestamp + stdout/stderr + flag)
        normalized = re.sub(k8s_prefix_pattern, '', normalized)
        
        # Replace ISO timestamps
        normalized = re.sub(iso_timestamp_pattern, '<TIMESTAMP>', normalized)
        
        # Replace standard MariaDB timestamps
        normalized = re.sub(timestamp_pattern, '<TIMESTAMP>', normalized)
        
        # Replace process IDs
        normalized = re.sub(pid_pattern, '<PID>', normalized)
        
        # Replace connection IDs
        normalized = re.sub(connection_id_pattern, '<CONN_ID>', normalized)
        
        # Replace numeric IDs (but keep error codes like [1234])
        # Only replace standalone numbers, not error codes in brackets
        # Do this BEFORE database.table replacement to avoid false matches
        normalized = re.sub(r'\b\d+\b', '<NUM>', normalized)
        # But restore error codes in brackets
        normalized = re.sub(r'\[<NUM>\]', '[<ERR_CODE>]', normalized)
        
        # Replace specific database/table names with placeholders
        # Pattern: database.table or `database`.`table`
        # Only match if both parts are word characters (not numbers)
        # Avoid matching version numbers like "1.2.11" or sizes like "12.000MiB"
        normalized = re.sub(
            r'`?([a-zA-Z_]\w*)`?\.`?([a-zA-Z_]\w*)`?',
            r'<DB>.<TABLE>',
            normalized
        )
        
        # Replace file paths (keep structure but normalize)
        normalized = re.sub(r'/[^\s]+', '<PATH>', normalized)
        
        # Determine severity
        severity = 'UNKNOWN'
        line_upper = line.upper()
        if any(kw in line_upper for kw in error_keywords):
            severity = 'ERROR'
        elif any(kw in line_upper for kw in warning_keywords):
            severity = 'WARNING'
        elif any(kw in line_upper for kw in info_keywords):
            severity = 'INFO'
        
        # Store pattern info
        if patterns[normalized]['sample_message'] is None:
            patterns[normalized]['sample_message'] = line[:200]  # Truncate long lines
        
        patterns[normalized]['count'] += 1
        patterns[normalized]['severity'] = severity
        
        if timestamp:
            if patterns[normalized]['first_seen'] is None:
                patterns[normalized]['first_seen'] = timestamp
            patterns[normalized]['last_seen'] = timestamp
    
    # Convert to list and sort by count (most frequent first)
    result = [
        {
            'pattern': pattern,
            'count': info['count'],
            'severity': info['severity'],
            'first_seen': info['first_seen'],
            'last_seen': info['last_seen'],
            'sample_message': info['sample_message'],
        }
        for pattern, info in patterns.items()
    ]
    
    # Sort by count descending, then by severity (ERROR > WARNING > INFO)
    severity_order = {'ERROR': 0, 'WARNING': 1, 'INFO': 2, 'UNKNOWN': 3}
    result.sort(key=lambda x: (-x['count'], severity_order.get(x['severity'], 99)))
    
    return result[:max_patterns]


def _get_skysql_logs_info(
    api_key: str,
    service_id: str,
    log_type: str,
    start_timestamp: str,
    end_timestamp: str,
    api_url: str,
    max_total_size: int = 10 * 1024 * 1024,  # 10MB default
) -> list[str]:
    """
    Get list of log IDs from SkySQL API for a given time range.
    
    Args:
        api_key: SkySQL API key
        service_id: Database service ID
        log_type: Type of log ('error-log' or 'slow-query-log')
        start_timestamp: Start time in ISO8601 format
        end_timestamp: End time in ISO8601 format
        api_url: SkySQL API base URL
        max_total_size: Maximum total size of log files in bytes (default: 10MB)
    
    Returns:
        List of log IDs
    """
    import requests
    import logging
    
    logger = logging.getLogger(__name__)
    
    headers = {
        "X-API-Key": api_key,
        "Content-Type": "application/json",
    }
    
    params = {
        "logType": log_type,
        "fromDate": start_timestamp,
        "toDate": end_timestamp,
    }
    
    try:
        response = requests.get(api_url, headers=headers, params=params, timeout=30)
    except Exception as e:
        logger.error(f"Error from SkySQL log info service: {str(e)}")
        raise Exception(f"Error from SkySQL log info service: {str(e)}") from e
    
    if response.status_code != 200:
        raise Exception(
            f"Unexpected response code {response.status_code} from SkySQL log info service: "
            f"{response.text}"
        )
    
    payload = response.json()
    logids = []
    total_logfiles_size = -1
    
    for log in payload.get("logs", []):
        # Match logs for this service_id
        server_ds_id = log.get("serverDataSourceId", "")
        if server_ds_id.split("/")[0] == service_id:
            total_logfiles_size += log.get("size", 0)
            logids.append(log["id"])
    
    if len(logids) == 0:
        raise Exception(f"No {log_type} files available for service_id {service_id}")
    
    if total_logfiles_size > max_total_size:
        raise Exception(
            f"Total size of {log_type} files ({total_logfiles_size} bytes) exceeds maximum "
            f"({max_total_size} bytes). Please review logs in the SkySQL portal."
        )
    
    return logids


def _get_skysql_logs_archive(
    api_key: str,
    log_type: str,
    logids: list[str],
    api_url: str,
) -> bytes:
    """
    Download log files archive from SkySQL API.
    
    Args:
        api_key: SkySQL API key
        log_type: Type of log ('error-log' or 'slow-query-log')
        logids: List of log IDs to download
        api_url: SkySQL API base URL
    
    Returns:
        Bytes content of the zip archive
    """
    import requests
    import logging
    
    logger = logging.getLogger(__name__)
    
    headers = {
        "X-API-Key": api_key,
        "Content-Type": "application/json",
    }
    
    params = {
        "logType": log_type,
        "logIds": ",".join(logids),
        "logFormat": "raw",
    }
    
    archive_url = f"{api_url}/archive"
    
    try:
        response = requests.get(archive_url, headers=headers, params=params, timeout=60)
    except Exception as e:
        logger.error(f"Error from SkySQL log archive service: {str(e)}")
        raise Exception(f"Error from SkySQL log archive service: {str(e)}") from e
    
    if response.status_code != 200:
        raise Exception(
            f"Unexpected response code {response.status_code} from SkySQL log archive service: "
            f"{response.text}"
        )
    
    return response.content


def _read_large_zipfile_in_reverse(
    zip_ref,
    file_path: str,
    buffer_size: int = 8192,
):
    """
    Read a file from a zip archive in reverse order (most recent lines first).
    
    This is useful for reading log files where we want the most recent entries.
    """
    with zip_ref.open(file_path) as file:
        # Seek to the end of the file
        file.seek(0, 2)  # Move to the end
        file_size = file.tell()
        
        buffer = ""
        position = file_size
        
        while position > 0:
            # Determine the size of the chunk to read
            read_size = min(buffer_size, position)
            position -= read_size
            file.seek(position)
            
            # Read and prepend to the buffer
            data = file.read(read_size).decode("utf-8", errors="ignore")
            buffer = data + buffer
            
            # Process complete lines in the buffer
            buffer, *lines = buffer.split("\n")
            
            for line in reversed(lines):
                yield line
        
        # Handle any remaining line in the buffer
        if buffer:
            yield buffer


def _load_skysql_errors(
    payload: bytes,
    start_timestamp: str,
    end_timestamp: str,
    max_lines: int = 5000,
) -> list[str]:
    """
    Extract error log lines from SkySQL log archive zip file.
    
    Args:
        payload: Zip file content as bytes
        start_timestamp: Start time in ISO8601 format
        end_timestamp: End time in ISO8601 format
        max_lines: Maximum number of lines to return
    
    Returns:
        List of error log lines (most recent first)
    """
    import io
    import zipfile
    from datetime import UTC, datetime, timedelta
    from dateutil import parser
    
    stream = io.BytesIO(payload)
    log_lines = []
    
    with zipfile.ZipFile(stream, "r") as zip_ref:
        filenames = zip_ref.namelist()
        
        start_datetime = parser.isoparse(start_timestamp)
        end_datetime = parser.isoparse(end_timestamp)
        
        # If start == end, expand to full day
        if start_timestamp == end_timestamp:
            end_datetime += timedelta(hours=23, minutes=59, seconds=59)
        
        for filename in filenames:
            # Parse filename: service_id_database_id_hostname_error-log_YYYY-MM-DD.log
            metadata = filename.split("_")
            if len(metadata) < 4:
                continue
            
            # Extract date from filename (format: YYYY-MM-DD.log)
            time_part = metadata[-1] if len(metadata) > 3 else None
            if time_part:
                try:
                    date_part = time_part.split(".")[0]  # Remove .log extension
                    time_parts = date_part.split("-")
                    if len(time_parts) == 3:
                        year = int(time_parts[0])
                        month = int(time_parts[1])
                        day = int(time_parts[2])
                        logfile_datetime = datetime(year, month, day, tzinfo=UTC)
                        logfile_datetime_end = logfile_datetime + timedelta(
                            hours=23, minutes=59, seconds=59
                        )
                        
                        # Skip if log file is outside time range
                        if not (
                            start_datetime <= logfile_datetime <= end_datetime
                            or start_datetime <= logfile_datetime_end <= end_datetime
                        ):
                            continue
                except (ValueError, IndexError):
                    # If we can't parse the date, include the file anyway
                    pass
            
            # Read file in reverse order
            for logline in _read_large_zipfile_in_reverse(zip_ref, filename):
                # Filter for ERROR and WARNING messages
                if not (
                    "[ERROR]" in logline or "[Warning]" in logline
                ):
                    continue
                
                # Skip certain warnings
                if (
                    "[Warning] Aborted connection" in logline
                    or "[Warning] Access denied for user" in logline
                ):
                    continue
                
                # Check timestamp if time range is specified
                if start_timestamp != end_timestamp:
                    try:
                        # Extract timestamp from log line (first part before space)
                        timestamp_str = logline.split(" ")[0]
                        log_time = parser.isoparse(timestamp_str)
                        if not (start_datetime <= log_time <= end_datetime):
                            # Since we're reading in reverse, if we're past the end time, break
                            if log_time > end_datetime:
                                break
                            continue
                    except (ValueError, IndexError):
                        # If we can't parse timestamp, include the line anyway
                        pass
                
                log_lines.append(logline)
                
                if len(log_lines) >= max_lines:
                    break
            
            if len(log_lines) >= max_lines:
                break
    
    return log_lines


def tail_error_log_file(
    service_id: str | None = None,
    path: str | None = None,
    max_bytes: int = 1_000_000,
    tail_lines: int = 5000,
    extract_patterns: bool = True,
    max_patterns: int = 20,
) -> Dict[str, Any]:
    """
    Read the tail of the MariaDB error log file and optionally extract patterns.
    
    Supports two modes:
    1. Local file access (for development/testing): reads from filesystem
    2. SkySQL API (for production): calls vendor-specific API
    
    Args:
        service_id: Database service identifier (for SkySQL API)
        path: Absolute path to error log file (for local file access)
        max_bytes: Maximum number of bytes to read from the end (default: 1_000_000)
        tail_lines: Approximate number of lines from the end (default: 5000)
        extract_patterns: If True, extract and group error patterns (default: True)
        max_patterns: Maximum number of unique patterns to return (default: 20)
    
    Returns:
        Dictionary with:
        - content: Raw log content (if extract_patterns=False)
        - patterns: List of error patterns (if extract_patterns=True)
        - total_lines: Total number of lines processed
        - source: 'local_file' or 'skysql_api'
    """
    import os
    import logging
    from datetime import UTC, datetime, timedelta
    
    logger = logging.getLogger(__name__)
    
    # Try SkySQL API first if service_id provided
    if service_id:
        try:
            from .config import SkySQLConfig
            
            skysql_config = SkySQLConfig.from_env()
            
            # Calculate time range (default: last 24 hours)
            end_time = datetime.now(UTC)
            start_time = end_time - timedelta(hours=24)
            
            start_timestamp = start_time.isoformat(timespec="seconds").split("+")[0] + "Z"
            end_timestamp = end_time.isoformat(timespec="seconds").split("+")[0] + "Z"
            
            # Get log IDs
            logids = _get_skysql_logs_info(
                api_key=skysql_config.api_key,
                service_id=service_id,
                log_type="error-log",
                start_timestamp=start_timestamp,
                end_timestamp=end_timestamp,
                api_url=skysql_config.api_url,
            )
            
            # Download log archive
            payload = _get_skysql_logs_archive(
                api_key=skysql_config.api_key,
                log_type="error-log",
                logids=logids,
                api_url=skysql_config.api_url,
            )
            
            # Extract error log lines
            log_lines = _load_skysql_errors(
                payload=payload,
                start_timestamp=start_timestamp,
                end_timestamp=end_timestamp,
                max_lines=tail_lines,
            )
            
            content = "\n".join(log_lines)
            total_lines = len(log_lines)
            
            if extract_patterns:
                patterns = extract_error_log_patterns(content, max_patterns=max_patterns)
                return {
                    "patterns": patterns,
                    "total_lines": total_lines,
                    "source": "skysql_api",
                }
            else:
                return {
                    "content": content,
                    "total_lines": total_lines,
                    "source": "skysql_api",
                }
                
        except ImportError:
            raise RuntimeError(
                "SkySQL API access requires SKYSQL_API_KEY environment variable. "
                "Set this in your .env file or environment. "
                "You can generate an API key at https://id.mariadb.com/account/api/"
            )
        except Exception as e:
            logger.error(f"Error fetching error logs from SkySQL API: {str(e)}")
            raise
    
    # Try local file access if path provided
    if path:
        if not os.path.exists(path):
            raise FileNotFoundError(f"Error log file not found: {path}")
        
        if not os.path.isfile(path):
            raise ValueError(f"Path is not a file: {path}")
        
        # Read tail of file
        file_size = os.path.getsize(path)
        bytes_to_read = min(max_bytes, file_size)
        
        with open(path, 'r', encoding='utf-8', errors='ignore') as f:
            if bytes_to_read < file_size:
                # Seek to position
                f.seek(file_size - bytes_to_read)
                # Skip partial line
                f.readline()
            
            content = f.read()
            lines = content.split('\n')
            total_lines = len(lines)
            
            # Limit to tail_lines if specified
            if tail_lines and total_lines > tail_lines:
                content = '\n'.join(lines[-tail_lines:])
                total_lines = tail_lines
        
        if extract_patterns:
            patterns = extract_error_log_patterns(content, max_patterns=max_patterns)
            return {
                'patterns': patterns,
                'total_lines': total_lines,
                'source': 'local_file',
            }
        else:
            return {
                'content': content,
                'total_lines': total_lines,
                'source': 'local_file',
            }
    
    # Neither service_id nor path provided
    raise ValueError(
        "Either service_id (for SkySQL API) or path (for local file) must be provided"
    )

