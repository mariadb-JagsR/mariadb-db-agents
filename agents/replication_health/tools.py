# agents/replication_health/tools.py
"""Tools for replication health analysis."""

from __future__ import annotations

import logging
from typing import Any
from agents import function_tool
from ...common.db_client import run_readonly_query
from ...common.config import DBConfig

logger = logging.getLogger(__name__)


@function_tool
def execute_sql(
    sql: str,
    max_rows: int = 1000,
    timeout_seconds: int = 10,
    database: str | None = None,
) -> dict[str, Any]:
    """
    Execute a read-only SQL query against a MariaDB / MariaDB Cloud instance.
    
    Database connection is configured via environment variables (DB_HOST, DB_PORT, DB_USER, DB_PASSWORD, DB_DATABASE).

    Use this to:
    - Query replication status
    - Check binlog information
    - Query processlist for replication-related queries
    - Get replication variables and status
    - Analyze binlog events

    Args:
        sql: Read-only SQL statement to execute
        max_rows: Maximum number of rows to return (default: 1000)
        timeout_seconds: Query timeout in seconds (default: 10)
        database: Optional database name to use

    Returns:
        Dictionary with 'rows' key containing the query results
    """
    rows = run_readonly_query(
        sql=sql,
        max_rows=max_rows,
        timeout_seconds=timeout_seconds,
        database=database,
    )
    return {"rows": rows}


@function_tool
def get_all_replica_status(
    max_executions: int = 10,
) -> dict[str, Any]:
    """
    Get replication status from all replicas in a SkySQL service.
    
    This function works around MaxScale load balancing by executing
    SHOW ALL SLAVES STATUS multiple times. Each execution may be
    routed to a different replica by MaxScale's round-robin algorithm.
    
    In SkySQL, there can be a maximum of 5 replicas, so executing
    10 times ensures we discover all replicas.
    
    Args:
        max_executions: Number of times to execute the query (default: 10)
                       This should be sufficient for SkySQL's max of 5 replicas
    
    Returns:
        Dictionary with:
        - 'replicas': List of replica status dictionaries (one per unique replica)
        - 'count': Number of unique replicas found
        - 'executions': Number of times query was executed
        - 'max_expected': Maximum expected replicas (5 for SkySQL)
        - 'note': Information about the approach used
    """
    import mysql.connector
    from ...common.config import DBConfig
    
    cfg = DBConfig.from_env()
    
    # Check if this is a SkySQL environment
    is_skysql = 'skysql.com' in cfg.host.lower()
    
    all_results = []
    seen_replicas = {}  # Keyed by unique identifier
    
    # For SkySQL/MaxScale: We need to create separate connections for each execution
    # to ensure MaxScale routes each to a different server (master or replica)
    # We only collect results when connected to the master (read_only=OFF)
    
    connect_kwargs = {
        'host': cfg.host,
        'port': cfg.port,
        'user': cfg.user,
        'password': cfg.password,
        'connection_timeout': 10,
    }
    
    if 'skysql.com' not in cfg.host.lower():
        connect_kwargs['ssl_disabled'] = True
    
    # Track which servers we hit (master vs replica)
    master_hits = 0
    replica_hits = 0
    total_executions = 0
    
    # Execute multiple times with separate connections to leverage MaxScale round-robin
    for i in range(max_executions):
        conn = None
        try:
            # Create a new connection for each execution
            # This ensures MaxScale can route each to a different server
            conn = mysql.connector.connect(**connect_kwargs)
            cursor = conn.cursor(dictionary=True)
            
            # Set autocommit to make each query a separate transaction
            # This helps MaxScale route each execution to a different server
            cursor.execute("SET autocommit = 1")
            
            # Check if we're connected to master or replica
            # Only collect results when connected to master (where SHOW ALL SLAVES STATUS shows replica connections)
            cursor.execute("SELECT @@read_only as read_only, @@log_bin as log_bin, @@server_id as server_id")
            server_info = cursor.fetchone()
            is_master = server_info.get('read_only') == 0 and server_info.get('log_bin') == 1
            
            total_executions += 1
            if is_master:
                master_hits += 1
            else:
                replica_hits += 1
            
            if not is_master:
                # We're connected to a replica - SHOW ALL SLAVES STATUS won't show useful info
                # Skip this execution and try again
                cursor.close()
                conn.close()
                continue
            
            # We're on the master - SHOW ALL SLAVES STATUS will show replica connections
            cursor.execute("SHOW ALL SLAVES STATUS")
            results = cursor.fetchall()
            
            for row in results:
                # Create a unique identifier for each replica connection
                # Use combination of Server_id, Master_Host, Master_Port, and Connection_name
                # This ensures we identify unique replica connections correctly
                server_id = row.get('Server_id') or row.get('Master_Server_Id') or 'unknown'
                master_host = row.get('Master_Host') or row.get('Source_Host') or 'unknown'
                master_port = row.get('Master_Port') or row.get('Source_Port') or 'unknown'
                conn_name = row.get('Connection_name') or ''
                
                # Create unique identifier: Server_id + Master_Host + Master_Port + Connection_name
                # This uniquely identifies each replica connection
                identifier = f"{server_id}_{master_host}_{master_port}_{conn_name}".strip('_')
                
                # Only keep first occurrence of each unique replica connection
                if identifier not in seen_replicas:
                    seen_replicas[identifier] = row
                    all_results.append(row)
            
            cursor.close()
            conn.close()
        
        except Exception as e:
            # Log error but continue with next execution
            logger.debug(f"Execution {i+1} of get_all_replica_status: {e}")
            if conn and conn.is_connected():
                try:
                    conn.close()
                except Exception:
                    pass
            continue
    
    # Note: We don't need a finally block here since we close connections in the loop
    
    # Detect if we're only hitting master (possible high lag scenario)
    only_master_hits = is_skysql and total_executions > 0 and master_hits == total_executions and len(seen_replicas) == 0
    
    note = (
        f"Executed SHOW ALL SLAVES STATUS {max_executions} times via MaxScale round-robin. "
        f"Only collected results when connected to master (read_only=OFF, log_bin=ON). "
        f"Found {len(seen_replicas)} unique replica connection(s) (SkySQL max: 5 replicas). "
    )
    
    if is_skysql:
        note += (
            "MaxScale round-robin routes queries to both master and replicas. "
            "We filter to only collect results from master connections to avoid duplicates. "
        )
        
        # Add warning if we only hit master (possible high lag scenario)
        if only_master_hits:
            note += (
                f"⚠️ WARNING: All {total_executions} executions were routed to the master (replica_hits=0). "
                "This may indicate HIGH REPLICATION LAG - MaxScale may be routing all traffic to the primary "
                "to avoid stale reads. If replicas exist, they may be significantly behind. "
                "Consider checking replication lag directly or waiting for lag to decrease before retrying."
            )
        elif total_executions > 0:
            note += f"Server routing: {master_hits} master hits, {replica_hits} replica hits out of {total_executions} executions."
    else:
        note += "Note: Non-SkySQL environment - results may vary."
    
    return {
        "replicas": list(seen_replicas.values()),
        "count": len(seen_replicas),
        "executions": max_executions,
        "max_expected": 5,  # SkySQL maximum
        "note": note,
        "routing_info": {
            "total_executions": total_executions,
            "master_hits": master_hits,
            "replica_hits": replica_hits,
            "only_master_hits": only_master_hits if is_skysql else False,
        } if is_skysql else None,
    }


@function_tool
def get_master_status() -> dict[str, Any]:
    """
    Get master/replication source status.
    
    In SkySQL/MaxScale environment, this will hit the primary server.
    Returns binlog position, file, and GTID information.
    
    Returns:
        Dictionary with:
        - 'available': Whether master status is available
        - 'status': Master status dictionary (if available)
        - 'note': Additional information
    """
    try:
        results = run_readonly_query(
            sql="SHOW MASTER STATUS",
            max_rows=10,
            timeout_seconds=10,
        )
        
        if not results:
            return {
                "available": False,
                "status": None,
                "note": "SHOW MASTER STATUS returned no results. This server may not be configured as a master, or replication may not be enabled."
            }
        
        return {
            "available": True,
            "status": results[0] if results else None,
            "note": "Master status retrieved successfully."
        }
    
    except Exception as e:
        logger.error(f"Error getting master status: {e}")
        return {
            "available": False,
            "status": None,
            "note": f"Error retrieving master status: {str(e)}"
        }


@function_tool
def get_replication_configuration() -> dict[str, Any]:
    """
    Get replication-related configuration variables.
    
    Returns replication settings including:
    - server_id, log_bin, binlog_format
    - GTID settings
    - Read-only settings
    - Binlog retention settings
    
    Returns:
        Dictionary with:
        - 'configuration': Dictionary of variable names and values
        - 'is_replica': Whether this server is configured as a replica (read_only)
        - 'is_master': Whether this server is configured as a master (log_bin enabled)
        - 'gtid_enabled': Whether GTID is enabled
        - 'note': Additional information
    """
    try:
        # Get replication variables
        variables = run_readonly_query(
            sql="""
            SELECT VARIABLE_NAME, VARIABLE_VALUE
            FROM information_schema.GLOBAL_VARIABLES
            WHERE VARIABLE_NAME IN (
                'server_id',
                'log_bin',
                'binlog_format',
                'sync_binlog',
                'expire_logs_days',
                'gtid_domain_id',
                'gtid_strict_mode',
                'read_only',
                'super_read_only',
                'relay_log',
                'relay_log_recovery'
            )
            ORDER BY VARIABLE_NAME
            """,
            max_rows=50,
            timeout_seconds=10,
        )
        
        config = {v['VARIABLE_NAME']: v['VARIABLE_VALUE'] for v in variables}
        
        # Determine server role
        is_replica = (
            config.get('read_only') == 'ON' or 
            config.get('super_read_only') == 'ON'
        )
        is_master = config.get('log_bin') == 'ON'
        
        # Check GTID
        gtid_domain_id = config.get('gtid_domain_id')
        gtid_enabled = (
            gtid_domain_id is not None and 
            gtid_domain_id != '0' and 
            gtid_domain_id != ''
        )
        
        return {
            "configuration": config,
            "is_replica": is_replica,
            "is_master": is_master,
            "gtid_enabled": gtid_enabled,
            "note": "Replication configuration retrieved successfully."
        }
    
    except Exception as e:
        logger.error(f"Error getting replication configuration: {e}")
        return {
            "configuration": {},
            "is_replica": False,
            "is_master": False,
            "gtid_enabled": False,
            "note": f"Error retrieving replication configuration: {str(e)}"
        }

