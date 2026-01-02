#!/usr/bin/env python3
"""
Comprehensive Concurrent Database Workload Test

This script creates a realistic, unpredictable database workload by running multiple
scenarios concurrently with random timing and intensities. It's designed to simulate
real-world database stress conditions.

Usage:
    python comprehensive_workload_test.py --duration 300
    python comprehensive_workload_test.py --duration 600 --intensity high
    python comprehensive_workload_test.py --duration 120 --scenarios lock,write,io
"""

import argparse
import asyncio
import logging
import random
import sys
import time
import threading
from pathlib import Path
from typing import List, Optional, Set
from collections import defaultdict

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


class ComprehensiveWorkloadTest:
    """
    Comprehensive workload test that runs multiple scenarios concurrently
    with random timing and intensities to create unpredictable load.
    """
    
    def __init__(
        self,
        config: DBConfig,
        duration: int = 300,
        intensity: str = "medium",
        enabled_scenarios: Optional[Set[str]] = None,
    ):
        self.config = config
        self.duration = duration
        self.intensity = intensity
        self.enabled_scenarios = enabled_scenarios or set()
        self.running = False
        self.connections: List[mysql.connector.MySQLConnection] = []
        self.threads: List[threading.Thread] = []
        self.active_scenarios = defaultdict(int)
        
        # Intensity settings
        intensity_configs = {
            "low": {"threads_multiplier": 0.5, "delay_range": (2, 5), "batch_size": 100},
            "medium": {"threads_multiplier": 1.0, "delay_range": (1, 3), "batch_size": 500},
            "high": {"threads_multiplier": 2.0, "delay_range": (0.5, 1.5), "batch_size": 1000},
        }
        self.intensity_config = intensity_configs.get(intensity, intensity_configs["medium"])
    
    def create_connection(self) -> Optional[mysql.connector.MySQLConnection]:
        """Create a test connection."""
        try:
            connect_kwargs = {
                'host': self.config.host,
                'port': self.config.port,
                'user': self.config.user,
                'password': self.config.password,
                'database': self.config.database,
                'connection_timeout': 10,
            }
            
            if 'skysql.com' not in self.config.host.lower():
                connect_kwargs['ssl_disabled'] = True
            
            conn = mysql.connector.connect(**connect_kwargs)
            # Add to tracking list (with safety limit to prevent excessive memory)
            if len(self.connections) < 2000:  # Safety limit
                self.connections.append(conn)
            return conn
        except MySQLError as e:
            logger.error(f"Failed to create connection: {e}")
            return None
    
    def remove_connection(self, conn: mysql.connector.MySQLConnection):
        """Remove a connection from the tracking list (thread-safe)."""
        try:
            if conn in self.connections:
                self.connections.remove(conn)
        except (ValueError, AttributeError):
            # Connection not in list or list modified - ignore
            pass
    
    def setup_tables(self):
        """Setup all test tables needed for various scenarios."""
        conn = self.create_connection()
        if not conn:
            return False
        
        try:
            cursor = conn.cursor()
            
            # Lock contention table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS test_lock_table (
                    id INT PRIMARY KEY AUTO_INCREMENT,
                    value INT,
                    data VARCHAR(100),
                    INDEX idx_value (value)
                ) ENGINE=InnoDB
            """)
            
            # Large table for I/O tests
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
            
            # Write load table
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
            
            # Memory pressure table (for temp table tests)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS test_memory_pressure (
                    id INT PRIMARY KEY AUTO_INCREMENT,
                    category VARCHAR(50),
                    value1 INT,
                    value2 INT,
                    value3 INT,
                    data TEXT,
                    INDEX idx_category (category)
                ) ENGINE=InnoDB
            """)
            
            # Populate lock table if needed
            cursor.execute("SELECT COUNT(*) FROM test_lock_table")
            if cursor.fetchone()[0] < 100:
                cursor.execute("""
                    INSERT INTO test_lock_table (value, data)
                    SELECT FLOOR(RAND() * 1000), CONCAT('data_', FLOOR(RAND() * 10000))
                    FROM (SELECT 1 UNION SELECT 2 UNION SELECT 3 UNION SELECT 4 UNION SELECT 5
                          UNION SELECT 6 UNION SELECT 7 UNION SELECT 8 UNION SELECT 9 UNION SELECT 10) AS t1
                    CROSS JOIN (SELECT 1 UNION SELECT 2 UNION SELECT 3 UNION SELECT 4 UNION SELECT 5
                                UNION SELECT 6 UNION SELECT 7 UNION SELECT 8 UNION SELECT 9 UNION SELECT 10) AS t2
                """)
            
            # Populate large table if needed
            cursor.execute("SELECT COUNT(*) FROM test_large_table")
            count = cursor.fetchone()[0]
            if count < 50000:
                logger.info("Populating large table...")
                for batch in range(50):
                    cursor.execute("""
                        INSERT INTO test_large_table (value1, value2, value3, value4)
                        SELECT FLOOR(RAND() * 1000), FLOOR(RAND() * 1000),
                               CONCAT('data_', FLOOR(RAND() * 10000)), REPEAT('x', 100)
                        FROM (SELECT 1 UNION SELECT 2 UNION SELECT 3 UNION SELECT 4 UNION SELECT 5
                              UNION SELECT 6 UNION SELECT 7 UNION SELECT 8 UNION SELECT 9 UNION SELECT 10) AS t1
                        CROSS JOIN (SELECT 1 UNION SELECT 2 UNION SELECT 3 UNION SELECT 4 UNION SELECT 5
                                    UNION SELECT 6 UNION SELECT 7 UNION SELECT 8 UNION SELECT 9 UNION SELECT 10) AS t2
                    """)
                    if batch % 10 == 0:
                        conn.commit()
            
            # Populate memory pressure table
            cursor.execute("SELECT COUNT(*) FROM test_memory_pressure")
            if cursor.fetchone()[0] < 1000:
                cursor.execute("""
                    INSERT INTO test_memory_pressure (category, value1, value2, value3, data)
                    SELECT 
                        CASE (seq % 10)
                            WHEN 0 THEN 'cat_a' WHEN 1 THEN 'cat_b' WHEN 2 THEN 'cat_c'
                            WHEN 3 THEN 'cat_d' WHEN 4 THEN 'cat_e' WHEN 5 THEN 'cat_f'
                            WHEN 6 THEN 'cat_g' WHEN 7 THEN 'cat_h' WHEN 8 THEN 'cat_i'
                            ELSE 'cat_j'
                        END,
                        FLOOR(RAND() * 1000), FLOOR(RAND() * 1000), FLOOR(RAND() * 1000),
                        REPEAT('x', 500)
                    FROM (SELECT 1 AS seq UNION SELECT 2 UNION SELECT 3 UNION SELECT 4 UNION SELECT 5
                          UNION SELECT 6 UNION SELECT 7 UNION SELECT 8 UNION SELECT 9 UNION SELECT 10) AS t1
                    CROSS JOIN (SELECT 1 UNION SELECT 2 UNION SELECT 3 UNION SELECT 4 UNION SELECT 5
                                UNION SELECT 6 UNION SELECT 7 UNION SELECT 8 UNION SELECT 9 UNION SELECT 10) AS t2
                    CROSS JOIN (SELECT 1 UNION SELECT 2 UNION SELECT 3 UNION SELECT 4 UNION SELECT 5
                                UNION SELECT 6 UNION SELECT 7 UNION SELECT 8 UNION SELECT 9 UNION SELECT 10) AS t3
                """)
            
            conn.commit()
            cursor.close()
            logger.info("Test tables ready")
            return True
        except MySQLError as e:
            logger.error(f"Failed to setup tables: {e}")
            return False
    
    def scenario_lock_contention(self):
        """Random lock contention - starts and stops randomly."""
        def blocking_worker():
            conn = self.create_connection()
            if not conn:
                return
            
            try:
                while self.running:
                    # Random delay before starting
                    time.sleep(random.uniform(*self.intensity_config["delay_range"]))
                    
                    if not self.running:
                        break
                    
                    cursor = conn.cursor()
                    cursor.execute("START TRANSACTION")
                    # Random range to lock
                    start_val = random.randint(1, 900)
                    end_val = start_val + random.randint(10, 100)
                    cursor.execute(
                        "SELECT * FROM test_lock_table WHERE value BETWEEN %s AND %s FOR UPDATE",
                        (start_val, end_val)
                    )
                    rows = cursor.fetchall()
                    
                    # Hold lock for random duration
                    hold_time = random.uniform(2, 10)
                    time.sleep(hold_time)
                    
                    cursor.execute("COMMIT")
                    cursor.close()
            except Exception as e:
                logger.debug(f"Lock contention worker error: {e}")
            finally:
                try:
                    if conn and conn.is_connected():
                        conn.close()
                    self.remove_connection(conn)
                except Exception:
                    pass
        
        def waiting_worker(worker_id: int):
            conn = self.create_connection()
            if not conn:
                return
            
            try:
                while self.running:
                    time.sleep(random.uniform(0.5, 2))
                    
                    if not self.running:
                        break
                    
                    cursor = conn.cursor()
                    # Try to update random range
                    start_val = random.randint(1, 900)
                    end_val = start_val + random.randint(5, 50)
                    cursor.execute(
                        "UPDATE test_lock_table SET data = CONCAT(data, '_u') WHERE value BETWEEN %s AND %s",
                        (start_val, end_val)
                    )
                    conn.commit()
                    cursor.close()
            except Exception as e:
                logger.debug(f"Waiting worker {worker_id} error (expected): {e}")
            finally:
                try:
                    if conn and conn.is_connected():
                        conn.close()
                    self.remove_connection(conn)
                except Exception:
                    pass
        
        # Start blocking workers
        num_blockers = max(1, int(2 * self.intensity_config["threads_multiplier"]))
        for i in range(num_blockers):
            thread = threading.Thread(target=blocking_worker, daemon=True)
            thread.start()
            self.threads.append(thread)
        
        # Start waiting workers
        num_waiters = max(3, int(5 * self.intensity_config["threads_multiplier"]))
        for i in range(num_waiters):
            thread = threading.Thread(target=waiting_worker, args=(i,), daemon=True)
            thread.start()
            self.threads.append(thread)
        
        self.active_scenarios["lock_contention"] += 1
    
    def scenario_long_running_queries(self):
        """Random long-running queries."""
        def long_query_worker(worker_id: int):
            conn = self.create_connection()
            if not conn:
                return
            
            try:
                while self.running:
                    # Random delay
                    time.sleep(random.uniform(*self.intensity_config["delay_range"]))
                    
                    if not self.running:
                        break
                    
                    cursor = conn.cursor()
                    # Random sleep duration
                    sleep_time = random.uniform(5, 30)
                    cursor.execute(f"SELECT SLEEP({sleep_time}), {worker_id} as worker_id")
                    cursor.fetchall()
                    cursor.close()
            except Exception as e:
                logger.debug(f"Long query worker {worker_id} error: {e}")
            finally:
                try:
                    if conn and conn.is_connected():
                        conn.close()
                    self.remove_connection(conn)
                except Exception:
                    pass
        
        num_workers = max(2, int(3 * self.intensity_config["threads_multiplier"]))
        for i in range(num_workers):
            thread = threading.Thread(target=long_query_worker, args=(i,), daemon=True)
            thread.start()
            self.threads.append(thread)
        
        self.active_scenarios["long_running"] += 1
    
    def scenario_io_intensive(self):
        """Random I/O intensive operations."""
        def io_worker(worker_id: int):
            conn = self.create_connection()
            if not conn:
                return
            
            try:
                while self.running:
                    time.sleep(random.uniform(*self.intensity_config["delay_range"]))
                    
                    if not self.running:
                        break
                    
                    cursor = conn.cursor()
                    # Random range scan (no index on value2)
                    start_val = random.randint(1, 900)
                    end_val = start_val + random.randint(10, 100)
                    cursor.execute(
                        "SELECT COUNT(*) FROM test_large_table WHERE value2 BETWEEN %s AND %s",
                        (start_val, end_val)
                    )
                    cursor.fetchall()
                    cursor.close()
            except Exception as e:
                logger.debug(f"I/O worker {worker_id} error: {e}")
            finally:
                try:
                    if conn and conn.is_connected():
                        conn.close()
                    self.remove_connection(conn)
                except Exception:
                    pass
        
        num_workers = max(2, int(4 * self.intensity_config["threads_multiplier"]))
        for i in range(num_workers):
            thread = threading.Thread(target=io_worker, args=(i,), daemon=True)
            thread.start()
            self.threads.append(thread)
        
        self.active_scenarios["io_intensive"] += 1
    
    def scenario_high_write_load(self):
        """Random high write load."""
        def write_worker(worker_id: int):
            conn = self.create_connection()
            if not conn:
                return
            
            try:
                batch_id = 0
                while self.running:
                    time.sleep(random.uniform(0.1, 1.0))
                    
                    if not self.running:
                        break
                    
                    cursor = conn.cursor()
                    batch_size = int(self.intensity_config["batch_size"] * random.uniform(0.5, 1.5))
                    rows_data = [
                        (worker_id, batch_id, f"data_{worker_id}_{batch_id}_{i}_" + "x" * 200)
                        for i in range(batch_size)
                    ]
                    cursor.executemany(
                        "INSERT INTO test_high_write_load (thread_id, batch_id, data) VALUES (%s, %s, %s)",
                        rows_data
                    )
                    conn.commit()
                    batch_id += 1
                    cursor.close()
            except Exception as e:
                logger.debug(f"Write worker {worker_id} error: {e}")
            finally:
                try:
                    if conn and conn.is_connected():
                        conn.close()
                    self.remove_connection(conn)
                except Exception:
                    pass
        
        num_workers = max(3, int(8 * self.intensity_config["threads_multiplier"]))
        for i in range(num_workers):
            thread = threading.Thread(target=write_worker, args=(i,), daemon=True)
            thread.start()
            self.threads.append(thread)
        
        self.active_scenarios["high_write_load"] += 1
    
    def scenario_memory_pressure(self):
        """Memory pressure - large temp tables."""
        def memory_worker(worker_id: int):
            conn = self.create_connection()
            if not conn:
                return
            
            try:
                while self.running:
                    time.sleep(random.uniform(2, 5))
                    
                    if not self.running:
                        break
                    
                    cursor = conn.cursor()
                    # Complex query that creates large temp tables
                    cursor.execute("""
                        SELECT 
                            category,
                            COUNT(*) as cnt,
                            AVG(value1) as avg1,
                            AVG(value2) as avg2,
                            AVG(value3) as avg3,
                            GROUP_CONCAT(data ORDER BY id LIMIT 100) as sample_data
                        FROM test_memory_pressure
                        WHERE value1 BETWEEN %s AND %s
                        GROUP BY category
                        ORDER BY cnt DESC
                    """, (random.randint(1, 500), random.randint(500, 1000)))
                    cursor.fetchall()
                    cursor.close()
            except Exception as e:
                logger.debug(f"Memory worker {worker_id} error: {e}")
            finally:
                try:
                    if conn and conn.is_connected():
                        conn.close()
                    self.remove_connection(conn)
                except Exception:
                    pass
        
        num_workers = max(2, int(3 * self.intensity_config["threads_multiplier"]))
        for i in range(num_workers):
            thread = threading.Thread(target=memory_worker, args=(i,), daemon=True)
            thread.start()
            self.threads.append(thread)
        
        self.active_scenarios["memory_pressure"] += 1
    
    def scenario_connection_churn(self):
        """Connection churn - rapid connect/disconnect."""
        def connection_churn_worker():
            while self.running:
                time.sleep(random.uniform(0.5, 2))
                
                if not self.running:
                    break
                
                conn = self.create_connection()
                if conn:
                    try:
                        cursor = conn.cursor()
                        cursor.execute("SELECT 1")
                        cursor.fetchone()
                        cursor.close()
                        # Hold connection briefly
                        time.sleep(random.uniform(0.1, 0.5))
                    except Exception:
                        pass
                    finally:
                        try:
                            if conn and conn.is_connected():
                                conn.close()
                            self.remove_connection(conn)
                        except Exception:
                            pass
        
        num_workers = max(5, int(10 * self.intensity_config["threads_multiplier"]))
        for i in range(num_workers):
            thread = threading.Thread(target=connection_churn_worker, daemon=True)
            thread.start()
            self.threads.append(thread)
        
        self.active_scenarios["connection_churn"] += 1
    
    def scenario_mixed_read_write(self):
        """Mixed read/write patterns."""
        def mixed_worker(worker_id: int):
            conn = self.create_connection()
            if not conn:
                return
            
            try:
                while self.running:
                    # Random operation type
                    op_type = random.choice(["read", "write", "read_write"])
                    time.sleep(random.uniform(0.2, 1.0))
                    
                    if not self.running:
                        break
                    
                    cursor = conn.cursor()
                    
                    if op_type == "read":
                        cursor.execute("SELECT COUNT(*) FROM test_high_write_load WHERE thread_id = %s", (worker_id,))
                        cursor.fetchone()
                    elif op_type == "write":
                        cursor.execute(
                            "INSERT INTO test_high_write_load (thread_id, batch_id, data) VALUES (%s, %s, %s)",
                            (worker_id, random.randint(1, 1000), f"mixed_write_{worker_id}_" + "x" * 100)
                        )
                        conn.commit()
                    else:  # read_write
                        cursor.execute("SELECT MAX(id) FROM test_high_write_load")
                        max_id = cursor.fetchone()[0] or 0
                        cursor.execute(
                            "INSERT INTO test_high_write_load (thread_id, batch_id, data) VALUES (%s, %s, %s)",
                            (worker_id, max_id + 1, f"mixed_rw_{worker_id}_" + "x" * 100)
                        )
                        conn.commit()
                    
                    cursor.close()
            except Exception as e:
                logger.debug(f"Mixed worker {worker_id} error: {e}")
            finally:
                try:
                    if conn and conn.is_connected():
                        conn.close()
                    self.remove_connection(conn)
                except Exception:
                    pass
        
        num_workers = max(3, int(5 * self.intensity_config["threads_multiplier"]))
        for i in range(num_workers):
            thread = threading.Thread(target=mixed_worker, args=(i,), daemon=True)
            thread.start()
            self.threads.append(thread)
        
        self.active_scenarios["mixed_read_write"] += 1
    
    def scenario_metadata_locks(self):
        """Metadata lock contention."""
        def metadata_worker(worker_id: int):
            conn = self.create_connection()
            if not conn:
                return
            
            try:
                while self.running:
                    time.sleep(random.uniform(1, 3))
                    
                    if not self.running:
                        break
                    
                    cursor = conn.cursor()
                    # Operations that acquire metadata locks
                    if random.random() < 0.5:
                        cursor.execute("SHOW CREATE TABLE test_high_write_load")
                        cursor.fetchone()
                    else:
                        cursor.execute("SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = DATABASE()")
                        cursor.fetchone()
                    cursor.close()
            except Exception as e:
                logger.debug(f"Metadata worker {worker_id} error: {e}")
            finally:
                try:
                    if conn and conn.is_connected():
                        conn.close()
                    self.remove_connection(conn)
                except Exception:
                    pass
        
        num_workers = max(2, int(3 * self.intensity_config["threads_multiplier"]))
        for i in range(num_workers):
            thread = threading.Thread(target=metadata_worker, args=(i,), daemon=True)
            thread.start()
            self.threads.append(thread)
        
        self.active_scenarios["metadata_locks"] += 1
    
    def run(self):
        """Run the comprehensive workload test."""
        if not self.setup_tables():
            logger.error("Failed to setup test tables")
            return False
        
        self.running = True
        logger.info(
            f"Starting comprehensive workload test "
            f"(duration: {self.duration}s, intensity: {self.intensity})"
        )
        
        # Available scenarios
        all_scenarios = {
            "lock": self.scenario_lock_contention,
            "long": self.scenario_long_running_queries,
            "io": self.scenario_io_intensive,
            "write": self.scenario_high_write_load,
            "memory": self.scenario_memory_pressure,
            "connections": self.scenario_connection_churn,
            "mixed": self.scenario_mixed_read_write,
            "metadata": self.scenario_metadata_locks,
        }
        
        # Determine which scenarios to run
        if self.enabled_scenarios:
            scenarios_to_run = {k: v for k, v in all_scenarios.items() if k in self.enabled_scenarios}
        else:
            # Run all by default
            scenarios_to_run = all_scenarios
        
        # Start all scenarios with random delays
        for scenario_name, scenario_func in scenarios_to_run.items():
            # Random delay before starting each scenario
            delay = random.uniform(0, 2)
            threading.Timer(delay, scenario_func).start()
            logger.info(f"Will start {scenario_name} scenario in {delay:.1f}s")
        
        # Monitor and log status periodically
        start_time = time.time()
        last_log = start_time
        
        try:
            while time.time() - start_time < self.duration:
                time.sleep(5)
                
                # Log status every 30 seconds
                if time.time() - last_log >= 30:
                    elapsed = time.time() - start_time
                    remaining = self.duration - elapsed
                    logger.info(
                        f"Workload running: {elapsed:.0f}s elapsed, {remaining:.0f}s remaining. "
                        f"Active threads: {threading.active_count()}, Connections: {len(self.connections)}"
                    )
                    last_log = time.time()
        except KeyboardInterrupt:
            logger.info("Interrupted by user")
        finally:
            self.cleanup()
        
        return True
    
    def cleanup(self):
        """Clean up all connections and threads."""
        logger.info("Cleaning up workload test...")
        self.running = False
        
        # Wait for threads to finish (with timeout)
        for thread in self.threads:
            thread.join(timeout=2)
        
        # Close connections safely - check if already closed
        # Use a copy of the list to avoid modification during iteration
        connections_to_close = list(self.connections)
        for conn in connections_to_close:
            try:
                # Check if connection exists and is still connected before closing
                if conn and hasattr(conn, 'is_connected'):
                    try:
                        if conn.is_connected():
                            conn.close()
                    except Exception:
                        # Connection might already be closed or in invalid state
                        pass
            except Exception:
                # Connection object might be invalid
                pass
        
        self.connections.clear()
        self.threads.clear()
        
        logger.info(f"Cleanup complete. Active scenarios: {dict(self.active_scenarios)}")


def main():
    parser = argparse.ArgumentParser(
        description="Comprehensive concurrent database workload test with unpredictable patterns"
    )
    parser.add_argument(
        "--duration",
        type=int,
        default=300,
        help="Test duration in seconds (default: 300)"
    )
    parser.add_argument(
        "--intensity",
        choices=["low", "medium", "high"],
        default="medium",
        help="Workload intensity (default: medium)"
    )
    parser.add_argument(
        "--scenarios",
        type=str,
        default=None,
        help="Comma-separated list of scenarios to run (lock,long,io,write,memory,connections,mixed,metadata). "
             "If not specified, all scenarios run."
    )
    
    args = parser.parse_args()
    
    # Load database config
    try:
        config = DBConfig.from_env()
    except Exception as e:
        logger.error(f"Failed to load database config: {e}")
        logger.error("Make sure .env file exists with DB_HOST, DB_PORT, DB_USER, DB_PASSWORD, DB_DATABASE")
        return 1
    
    # Parse enabled scenarios
    enabled_scenarios = None
    if args.scenarios:
        enabled_scenarios = set(s.strip() for s in args.scenarios.split(","))
        valid_scenarios = {"lock", "long", "io", "write", "memory", "connections", "mixed", "metadata"}
        invalid = enabled_scenarios - valid_scenarios
        if invalid:
            logger.error(f"Invalid scenarios: {invalid}. Valid: {valid_scenarios}")
            return 1
    
    # Create and run test
    test = ComprehensiveWorkloadTest(
        config=config,
        duration=args.duration,
        intensity=args.intensity,
        enabled_scenarios=enabled_scenarios,
    )
    
    try:
        success = test.run()
        return 0 if success else 1
    except Exception as e:
        logger.error(f"Error running workload test: {e}", exc_info=True)
        return 1


if __name__ == "__main__":
    sys.exit(main())

