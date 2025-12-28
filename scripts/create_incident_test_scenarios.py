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


class HighWriteLoadScenario(IncidentTestScenario):
    """
    Create high write load with high concurrency and large bulk writes.
    
    This scenario:
    - Creates multiple concurrent threads doing bulk INSERTs
    - Uses large batch sizes to maximize write throughput
    - Can generate replication lag if replicas exist
    - Tests database performance under heavy write load
    """
    
    def __init__(self, config: DBConfig, duration: int = 60, num_threads: int = 10, batch_size: int = 1000):
        super().__init__(config, duration)
        self.num_threads = num_threads
        self.batch_size = batch_size
    
    def setup(self):
        """Create test table if needed."""
        conn = self.create_connection()
        if not conn:
            return False
        
        try:
            cursor = conn.cursor()
            # Create test table optimized for writes
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS test_high_write_load (
                    id BIGINT PRIMARY KEY AUTO_INCREMENT,
                    thread_id INT,
                    batch_id INT,
                    data VARCHAR(500),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    INDEX idx_thread_batch (thread_id, batch_id),
                    INDEX idx_created (created_at)
                ) ENGINE=InnoDB
            """)
            
            # Truncate table to start fresh
            cursor.execute("TRUNCATE TABLE test_high_write_load")
            conn.commit()
            
            cursor.close()
            logger.info(f"High write load test table ready (threads: {self.num_threads}, batch_size: {self.batch_size})")
            return True
        except MySQLError as e:
            logger.error(f"Failed to setup high write load scenario: {e}")
            return False
    
    def run(self):
        """Run the high write load scenario."""
        if not self.setup():
            return
        
        self.running = True
        logger.info(
            f"Starting high write load scenario "
            f"(duration: {self.duration}s, threads: {self.num_threads}, batch_size: {self.batch_size})"
        )
        
        def bulk_writer(thread_id: int):
            """Thread that performs bulk writes continuously."""
            conn = self.create_connection()
            if not conn:
                return
            
            try:
                cursor = conn.cursor()
                batch_id = 0
                total_rows = 0
                
                # Keep writing until duration expires
                start_time = time.time()
                while self.running and (time.time() - start_time) < self.duration:
                    try:
                        # Build bulk INSERT data - no transaction overhead, direct commit
                        rows_data = []
                        for i in range(self.batch_size):
                            # Generate some data to write
                            data_value = f"thread_{thread_id}_batch_{batch_id}_row_{i}_" + "x" * 200
                            rows_data.append((thread_id, batch_id, data_value))
                        
                        # Execute bulk INSERT using executemany (safe and efficient)
                        sql = """
                            INSERT INTO test_high_write_load (thread_id, batch_id, data)
                            VALUES (%s, %s, %s)
                        """
                        cursor.executemany(sql, rows_data)
                        conn.commit()
                        
                        # No sleep - maximum throughput for replication lag generation
                        
                        total_rows += self.batch_size
                        batch_id += 1
                        
                        # Log progress every 10 batches
                        if batch_id % 10 == 0:
                            logger.debug(
                                f"Thread {thread_id}: inserted {total_rows} rows "
                                f"({batch_id} batches)"
                            )
                        
                        # No sleep - maximum throughput for replication lag generation
                        
                    except MySQLError as e:
                        logger.warning(f"Thread {thread_id} batch {batch_id} error: {e}")
                        try:
                            conn.rollback()
                        except Exception:
                            pass
                        # Minimal pause before retrying (only on error)
                        time.sleep(0.01)
                
                cursor.close()
                logger.info(
                    f"Thread {thread_id} completed: {total_rows} rows in {batch_id} batches"
                )
                
            except Exception as e:
                logger.error(f"Thread {thread_id} fatal error: {e}")
            finally:
                try:
                    if conn.is_connected():
                        conn.close()
                except Exception:
                    pass  # Ignore errors during cleanup
        
        # Start all writer threads immediately (no stagger for maximum concurrency)
        for i in range(self.num_threads):
            thread = threading.Thread(target=bulk_writer, args=(i,), daemon=True)
            thread.start()
            self.threads.append(thread)
        
        logger.info(f"Started {self.num_threads} writer threads")
        
        # Wait for duration
        time.sleep(self.duration)
        
        # Give threads a moment to finish current batches
        time.sleep(2)
        
        # Get final statistics
        try:
            conn = self.create_connection()
            if conn:
                cursor = conn.cursor()
                cursor.execute("SELECT COUNT(*) FROM test_high_write_load")
                total_rows = cursor.fetchone()[0]
                cursor.execute("SELECT COUNT(DISTINCT thread_id) FROM test_high_write_load")
                active_threads = cursor.fetchone()[0]
                cursor.close()
                conn.close()
                logger.info(
                    f"High write load completed: {total_rows} total rows written "
                    f"by {active_threads} threads"
                )
        except Exception as e:
            logger.warning(f"Could not get final statistics: {e}")
        
        self.cleanup()


def main():
    parser = argparse.ArgumentParser(
        description="Create test scenarios for Incident Triage Agent"
    )
    parser.add_argument(
        "--scenario",
        choices=["lock_contention", "long_running", "connection_exhaustion", "io_intensive", "high_write_load", "all"],
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
    parser.add_argument(
        "--num-threads",
        type=int,
        default=10,
        help="Number of concurrent threads for high_write_load scenario (default: 10)"
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=1000,
        help="Batch size (rows per INSERT) for high_write_load scenario (default: 1000)"
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
        cursor.execute("DROP TABLE IF EXISTS test_high_write_load")
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
            HighWriteLoadScenario(config, args.duration, args.num_threads, args.batch_size),
        ]
    elif args.scenario == "lock_contention":
        scenarios = [LockContentionScenario(config, args.duration)]
    elif args.scenario == "long_running":
        scenarios = [LongRunningQueryScenario(config, args.duration)]
    elif args.scenario == "connection_exhaustion":
        scenarios = [ConnectionExhaustionScenario(config, args.duration)]
    elif args.scenario == "io_intensive":
        scenarios = [IOIntensiveScenario(config, args.duration)]
    elif args.scenario == "high_write_load":
        scenarios = [HighWriteLoadScenario(config, args.duration, args.num_threads, args.batch_size)]
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

