#!/usr/bin/env python3
"""
Create test scenarios for Incident Triage Agent.

This script creates various database problems to test the Incident Triage Agent's
ability to detect and diagnose issues.

Usage:
    python create_incident_test_scenarios.py --scenario lock_contention
    python create_incident_test_scenarios.py --scenario connection_exhaustion --duration 60
    python create_incident_test_scenarios.py --scenario all --duration 120
"""

import argparse
import asyncio
import logging
import sys
import time
import threading
from pathlib import Path
from typing import List, Optional

import mysql.connector
from mysql.connector import Error as MySQLError

# Add parent directory to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from common.config import DBConfig

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
)
logger = logging.getLogger(__name__)


class IncidentTestScenario:
    """Base class for incident test scenarios."""
    
    def __init__(self, config: DBConfig, duration: int = 60):
        self.config = config
        self.duration = duration
        self.connections: List[mysql.connector.MySQLConnection] = []
        self.threads: List[threading.Thread] = []
        self.running = False
    
    def create_connection(self) -> Optional[mysql.connector.MySQLConnection]:
        """Create a test connection."""
        try:
            # Determine SSL configuration based on host
            connect_kwargs = {
                'host': self.config.host,
                'port': self.config.port,
                'user': self.config.user,
                'password': self.config.password,
                'database': self.config.database,
                'connection_timeout': 10,
            }
            
            # SkySQL instances require SSL - don't disable it
            if 'skysql.com' not in self.config.host.lower():
                # For non-SkySQL hosts, SSL may not be required
                connect_kwargs['ssl_disabled'] = True
            
            conn = mysql.connector.connect(**connect_kwargs)
            self.connections.append(conn)
            return conn
        except MySQLError as e:
            logger.error(f"Failed to create connection: {e}")
            return None
    
    def cleanup(self):
        """Clean up all test connections and threads."""
        logger.info("Cleaning up test scenario...")
        self.running = False
        
        # Wait for threads to finish
        for thread in self.threads:
            thread.join(timeout=5)
        
        # Close all connections
        for conn in self.connections:
            try:
                if conn.is_connected():
                    conn.close()
            except Exception as e:
                logger.warning(f"Error closing connection: {e}")
        
        self.connections.clear()
        self.threads.clear()
        logger.info("Cleanup complete")


class LockContentionScenario(IncidentTestScenario):
    """Create lock contention by having a long transaction block other queries."""
    
    def setup(self):
        """Create test table if needed."""
        conn = self.create_connection()
        if not conn:
            return False
        
        try:
            cursor = conn.cursor()
            # Create test table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS test_lock_table (
                    id INT PRIMARY KEY AUTO_INCREMENT,
                    value INT,
                    data VARCHAR(100),
                    INDEX idx_value (value)
                ) ENGINE=InnoDB
            """)
            
            # Insert some test data
            cursor.execute("SELECT COUNT(*) FROM test_lock_table")
            count = cursor.fetchone()[0]
            if count < 100:
                cursor.execute("""
                    INSERT INTO test_lock_table (value, data)
                    SELECT 
                        FLOOR(RAND() * 1000),
                        CONCAT('data_', FLOOR(RAND() * 10000))
                    FROM (
                        SELECT 1 UNION SELECT 2 UNION SELECT 3 UNION SELECT 4 UNION SELECT 5
                        UNION SELECT 6 UNION SELECT 7 UNION SELECT 8 UNION SELECT 9 UNION SELECT 10
                    ) AS t1
                    CROSS JOIN (
                        SELECT 1 UNION SELECT 2 UNION SELECT 3 UNION SELECT 4 UNION SELECT 5
                        UNION SELECT 6 UNION SELECT 7 UNION SELECT 8 UNION SELECT 9 UNION SELECT 10
                    ) AS t2
                """)
                conn.commit()
            
            cursor.close()
            logger.info("Lock contention test table ready")
            return True
        except MySQLError as e:
            logger.error(f"Failed to setup lock contention scenario: {e}")
            return False
    
    def run(self):
        """Run the lock contention scenario."""
        if not self.setup():
            return
        
        self.running = True
        logger.info(f"Starting lock contention scenario (duration: {self.duration}s)")
        
        # Thread 1: Long transaction that holds locks
        def blocking_transaction():
            conn = self.create_connection()
            if not conn:
                return
            
            try:
                cursor = conn.cursor()
                cursor.execute("START TRANSACTION")
                # Lock multiple rows to create more contention
                # Use a range that will match multiple rows
                cursor.execute("""
                    SELECT * FROM test_lock_table 
                    WHERE value BETWEEN 100 AND 200 
                    FOR UPDATE
                """)
                rows = cursor.fetchall()
                logger.info(f"Blocking transaction locked {len(rows)} rows")
                # Hold the lock for the duration - this creates real lock contention
                time.sleep(self.duration)
                cursor.execute("COMMIT")
                cursor.close()
            except Exception as e:
                logger.error(f"Blocking transaction error: {e}")
            finally:
                try:
                    if conn.is_connected():
                        conn.close()
                except Exception:
                    pass  # Ignore errors during cleanup
        
        # Thread 2-N: Queries that will wait for the lock
        def waiting_query(query_id: int):
            conn = self.create_connection()
            if not conn:
                return
            
            try:
                cursor = conn.cursor()
                # This will wait for the lock - try to update the same rows
                # This creates real lock contention
                cursor.execute("""
                    UPDATE test_lock_table 
                    SET data = CONCAT(data, '_updated') 
                    WHERE value BETWEEN 100 AND 200
                """)
                affected = cursor.rowcount
                conn.commit()
                logger.debug(f"Waiting query {query_id} updated {affected} rows after waiting")
                cursor.close()
            except Exception as e:
                logger.debug(f"Waiting query {query_id} error (expected): {e}")
            finally:
                try:
                    if conn.is_connected():
                        conn.close()
                except Exception:
                    pass  # Ignore errors during cleanup
        
        # Start blocking transaction
        blocker_thread = threading.Thread(target=blocking_transaction, daemon=True)
        blocker_thread.start()
        time.sleep(2)  # Give it time to acquire the lock
        
        # Start multiple waiting queries
        for i in range(5):
            thread = threading.Thread(target=waiting_query, args=(i,), daemon=True)
            thread.start()
            self.threads.append(thread)
            time.sleep(0.5)
        
        # Wait for duration
        time.sleep(self.duration)
        self.cleanup()


class LongRunningQueryScenario(IncidentTestScenario):
    """Create long-running queries."""
    
    def run(self):
        """Run the long-running query scenario."""
        self.running = True
        logger.info(f"Starting long-running query scenario (duration: {self.duration}s)")
        
        def long_query(query_id: int):
            conn = self.create_connection()
            if not conn:
                return
            
            try:
                cursor = conn.cursor()
                # Create a query that takes time
                # Using SLEEP in a subquery to simulate work
                cursor.execute(f"""
                    SELECT 
                        SLEEP({self.duration}),
                        '{query_id}' as query_id,
                        NOW() as start_time
                """)
                cursor.fetchall()
                cursor.close()
            except Exception as e:
                logger.debug(f"Long query {query_id} error: {e}")
            finally:
                if conn.is_connected():
                    conn.close()
        
        # Start multiple long-running queries
        for i in range(3):
            thread = threading.Thread(target=long_query, args=(i,), daemon=True)
            thread.start()
            self.threads.append(thread)
            time.sleep(1)
        
        # Wait for duration
        time.sleep(self.duration)
        self.cleanup()


class ConnectionExhaustionScenario(IncidentTestScenario):
    """Create connection exhaustion by opening many connections."""
    
    def run(self):
        """Run the connection exhaustion scenario."""
        self.running = True
        logger.info(f"Starting connection exhaustion scenario (duration: {self.duration}s)")
        
        def hold_connection(conn_id: int):
            conn = self.create_connection()
            if not conn:
                return
            
            try:
                # Hold the connection open
                time.sleep(self.duration)
            except Exception as e:
                logger.debug(f"Connection {conn_id} error: {e}")
            finally:
                if conn.is_connected():
                    conn.close()
        
        # Open many connections
        max_connections = 100  # Adjust based on your max_connections setting
        for i in range(min(max_connections - 10, 90)):  # Leave some headroom
            thread = threading.Thread(target=hold_connection, args=(i,), daemon=True)
            thread.start()
            self.threads.append(thread)
            time.sleep(0.1)  # Stagger connection creation
        
        logger.info(f"Opened {len(self.threads)} connections")
        
        # Wait for duration
        time.sleep(self.duration)
        self.cleanup()


class IOIntensiveScenario(IncidentTestScenario):
    """Create I/O intensive operations (large table scans)."""
    
    def setup(self):
        """Create large test table if needed."""
        conn = self.create_connection()
        if not conn:
            return False
        
        try:
            cursor = conn.cursor()
            # Create large test table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS test_large_table (
                    id INT PRIMARY KEY AUTO_INCREMENT,
                    value1 INT,
                    value2 INT,
                    value3 VARCHAR(100),
                    value4 TEXT,
                    INDEX idx_value1 (value1)
                ) ENGINE=InnoDB
            """)
            
            # Check if table has enough data
            cursor.execute("SELECT COUNT(*) FROM test_large_table")
            count = cursor.fetchone()[0]
            
            if count < 100000:
                logger.info("Populating large test table (this may take a while)...")
                # Insert data in batches
                for batch in range(100):  # 1000 rows per batch = 100k rows
                    cursor.execute("""
                        INSERT INTO test_large_table (value1, value2, value3, value4)
                        SELECT 
                            FLOOR(RAND() * 1000),
                            FLOOR(RAND() * 1000),
                            CONCAT('data_', FLOOR(RAND() * 10000)),
                            REPEAT('x', 100)
                        FROM (
                            SELECT 1 UNION SELECT 2 UNION SELECT 3 UNION SELECT 4 UNION SELECT 5
                            UNION SELECT 6 UNION SELECT 7 UNION SELECT 8 UNION SELECT 9 UNION SELECT 10
                        ) AS t1
                        CROSS JOIN (
                            SELECT 1 UNION SELECT 2 UNION SELECT 3 UNION SELECT 4 UNION SELECT 5
                            UNION SELECT 6 UNION SELECT 7 UNION SELECT 8 UNION SELECT 9 UNION SELECT 10
                        ) AS t2
                    """)
                    if batch % 10 == 0:
                        conn.commit()
                        logger.info(f"Inserted {(batch + 1) * 1000} rows...")
                
                conn.commit()
            
            cursor.close()
            logger.info("I/O intensive test table ready")
            return True
        except MySQLError as e:
            logger.error(f"Failed to setup I/O intensive scenario: {e}")
            return False
    
    def run(self):
        """Run the I/O intensive scenario."""
        if not self.setup():
            return
        
        self.running = True
        logger.info(f"Starting I/O intensive scenario (duration: {self.duration}s)")
        
        def io_intensive_query(query_id: int):
            conn = self.create_connection()
            if not conn:
                return
            
            try:
                cursor = conn.cursor()
                # Full table scan on large table (no index on value2)
                start_time = time.time()
                while time.time() - start_time < self.duration:
                    cursor.execute("""
                        SELECT COUNT(*) 
                        FROM test_large_table 
                        WHERE value2 BETWEEN 100 AND 200
                    """)
                    cursor.fetchall()
                    time.sleep(0.1)  # Small delay between scans
                cursor.close()
            except Exception as e:
                logger.debug(f"I/O query {query_id} error: {e}")
            finally:
                if conn.is_connected():
                    conn.close()
        
        # Start multiple I/O intensive queries
        for i in range(3):
            thread = threading.Thread(target=io_intensive_query, args=(i,), daemon=True)
            thread.start()
            self.threads.append(thread)
            time.sleep(1)
        
        # Wait for duration
        time.sleep(self.duration)
        self.cleanup()


def main():
    parser = argparse.ArgumentParser(
        description="Create test scenarios for Incident Triage Agent"
    )
    parser.add_argument(
        "--scenario",
        choices=["lock_contention", "long_running", "connection_exhaustion", "io_intensive", "all"],
        required=True,
        help="Scenario to create"
    )
    parser.add_argument(
        "--duration",
        type=int,
        default=60,
        help="Duration in seconds (default: 60)"
    )
    parser.add_argument(
        "--cleanup-only",
        action="store_true",
        help="Only cleanup test tables/connections, don't create problems"
    )
    
    args = parser.parse_args()
    
    # Load database config
    try:
        config = DBConfig.from_env()
    except Exception as e:
        logger.error(f"Failed to load database config: {e}")
        logger.error("Make sure .env file exists with DB_HOST, DB_PORT, DB_USER, DB_PASSWORD, DB_DATABASE")
        return 1
    
    if args.cleanup_only:
        logger.info("Cleanup mode - removing test tables...")
        # Determine SSL configuration
        connect_kwargs = {
            'host': config.host,
            'port': config.port,
            'user': config.user,
            'password': config.password,
            'database': config.database,
            'connection_timeout': 10,
        }
        # SkySQL instances require SSL - don't disable it
        if 'skysql.com' not in config.host.lower():
            connect_kwargs['ssl_disabled'] = True
        conn = mysql.connector.connect(**connect_kwargs)
        cursor = conn.cursor()
        cursor.execute("DROP TABLE IF EXISTS test_lock_table")
        cursor.execute("DROP TABLE IF EXISTS test_large_table")
        conn.commit()
        cursor.close()
        conn.close()
        logger.info("Cleanup complete")
        return 0
    
    scenarios = []
    
    if args.scenario == "all":
        scenarios = [
            LockContentionScenario(config, args.duration),
            LongRunningQueryScenario(config, args.duration),
            ConnectionExhaustionScenario(config, args.duration),
            IOIntensiveScenario(config, args.duration),
        ]
    elif args.scenario == "lock_contention":
        scenarios = [LockContentionScenario(config, args.duration)]
    elif args.scenario == "long_running":
        scenarios = [LongRunningQueryScenario(config, args.duration)]
    elif args.scenario == "connection_exhaustion":
        scenarios = [ConnectionExhaustionScenario(config, args.duration)]
    elif args.scenario == "io_intensive":
        scenarios = [IOIntensiveScenario(config, args.duration)]
    
    logger.info(f"Starting {len(scenarios)} scenario(s) for {args.duration} seconds...")
    logger.info("Press Ctrl+C to stop early")
    
    try:
        # Run scenarios
        for scenario in scenarios:
            scenario.run()
        
        logger.info("All scenarios completed")
        return 0
    except KeyboardInterrupt:
        logger.info("Interrupted by user, cleaning up...")
        for scenario in scenarios:
            scenario.cleanup()
        return 1
    except Exception as e:
        logger.error(f"Error running scenarios: {e}", exc_info=True)
        for scenario in scenarios:
            scenario.cleanup()
        return 1


if __name__ == "__main__":
    sys.exit(main())

