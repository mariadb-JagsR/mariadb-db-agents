#!/usr/bin/env python3
"""
Generate slow queries on beer_reviews database for testing the slow query agent.

REVIEWED VERSION - Safer queries that will be slow but not hang indefinitely.
"""

import mysql.connector
import time
import random
import sys
from pathlib import Path
from datetime import datetime, timedelta

# Add parent directory to path to import common modules
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))
from common.config import DBConfig

# SAFER slow queries - designed to be slow (>5 seconds) but not hang
SAFE_SLOW_QUERIES = [
    {
        "name": "Full table scan with text search (LIKE on TEXT column)",
        "query": """
            SELECT beer_name, beer_style, review_text, review_overall
            FROM beer_reviews_flat
            WHERE review_text LIKE '%delicious%'
               OR review_text LIKE '%excellent%'
               OR review_text LIKE '%amazing%'
            ORDER BY review_time DESC
            LIMIT 1000
        """,
        "why_slow": "Full table scan + text search on TEXT column (no index) + sorting"
    },
    {
        "name": "Complex aggregation with multiple GROUP BY columns",
        "query": """
            SELECT 
                beer_style,
                beer_brewerId,
                COUNT(*) as review_count,
                AVG(CAST(review_overall AS DECIMAL(5,2))) as avg_overall,
                AVG(CAST(review_appearance AS DECIMAL(5,2))) as avg_appearance,
                AVG(CAST(review_aroma AS DECIMAL(5,2))) as avg_aroma,
                AVG(CAST(review_taste AS DECIMAL(5,2))) as avg_taste,
                AVG(CAST(review_palate AS DECIMAL(5,2))) as avg_palate
            FROM beer_reviews_flat
            WHERE review_time >= DATE_SUB(NOW(), INTERVAL 10 YEAR)
            GROUP BY beer_style, beer_brewerId
            HAVING review_count > 50
            ORDER BY avg_overall DESC, review_count DESC
        """,
        "why_slow": "Multiple aggregations + GROUP BY on multiple columns + date filter"
    },
    {
        "name": "Complex text search with multiple LIKE conditions",
        "query": """
            SELECT 
                beer_name,
                beer_style,
                review_profileName,
                review_text,
                review_overall
            FROM beer_reviews_flat
            WHERE (review_text LIKE '%hoppy%' OR review_text LIKE '%bitter%')
              AND (review_text LIKE '%smooth%' OR review_text LIKE '%creamy%')
              AND CAST(review_overall AS DECIMAL(5,2)) >= 4.0
              AND review_time >= DATE_SUB(NOW(), INTERVAL 5 YEAR)
            ORDER BY CAST(review_overall AS DECIMAL(5,2)) DESC, review_time DESC
            LIMIT 500
        """,
        "why_slow": "Multiple LIKE conditions on TEXT column + type casting + sorting"
    },
    {
        "name": "Window function with complex partitioning",
        "query": """
            SELECT 
                beer_name,
                beer_style,
                review_profileName,
                review_overall,
                review_time,
                ROW_NUMBER() OVER (
                    PARTITION BY beer_style 
                    ORDER BY CAST(review_overall AS DECIMAL(5,2)) DESC
                ) as style_rank,
                AVG(CAST(review_overall AS DECIMAL(5,2))) OVER (
                    PARTITION BY beer_style
                ) as style_avg
            FROM beer_reviews_flat
            WHERE review_time >= DATE_SUB(NOW(), INTERVAL 3 YEAR)
            ORDER BY beer_style, style_rank
            LIMIT 2000
        """,
        "why_slow": "Window functions with partitioning + type casting + sorting large dataset"
    },
    {
        "name": "Complex date range with text analysis and aggregations",
        "query": """
            SELECT 
                DATE_FORMAT(review_time, '%Y-%m') as review_month,
                beer_style,
                COUNT(*) as review_count,
                AVG(CAST(review_overall AS DECIMAL(5,2))) as avg_rating,
                SUM(CASE WHEN review_text LIKE '%excellent%' THEN 1 ELSE 0 END) as excellent_count,
                SUM(CASE WHEN review_text LIKE '%poor%' OR review_text LIKE '%bad%' THEN 1 ELSE 0 END) as negative_count
            FROM beer_reviews_flat
            WHERE review_time >= DATE_SUB(NOW(), INTERVAL 10 YEAR)
              AND review_text IS NOT NULL
              AND LENGTH(review_text) > 50
            GROUP BY DATE_FORMAT(review_time, '%Y-%m'), beer_style
            HAVING review_count > 20
            ORDER BY review_month DESC, avg_rating DESC
        """,
        "why_slow": "Date formatting + text analysis + multiple aggregations + GROUP BY"
    },
    {
        "name": "Subquery with aggregation (safer than correlated)",
        "query": """
            SELECT 
                beer_name,
                beer_style,
                review_overall,
                review_time,
                (SELECT AVG(CAST(review_overall AS DECIMAL(5,2)))
                 FROM beer_reviews_flat b2
                 WHERE b2.beer_style = b1.beer_style
                ) as style_avg_rating,
                (SELECT COUNT(*)
                 FROM beer_reviews_flat b3
                 WHERE b3.beer_beerId = b1.beer_beerId
                ) as beer_review_count
            FROM beer_reviews_flat b1
            WHERE review_time >= DATE_SUB(NOW(), INTERVAL 1 YEAR)
            ORDER BY CAST(review_overall AS DECIMAL(5,2)) DESC
            LIMIT 1000
        """,
        "why_slow": "Subqueries executed for each row (though limited to 1000 rows)"
    }
]

# REMOVED QUERIES (too dangerous):
# 1. Self-join for finding similar beers - CROSS JOIN on 2.9M rows = disaster
# 2. Cross-product style comparison - CROSS JOIN = even worse
# 3. Correlated subquery version - runs subquery for every row in result set


def run_slow_queries(num_iterations=2):
    """
    Run slow queries multiple times to generate slow query log entries.
    
    Args:
        num_iterations: Number of times to run each query
    """
    cfg = DBConfig.from_env()
    
    # Override database to use beer_reviews
    conn = mysql.connector.connect(
        host=cfg.host,
        port=cfg.port,
        user=cfg.user,
        password=cfg.password,
        database='beer_reviews',
        ssl_disabled=True,
        connection_timeout=30,
    )
    
    cursor = conn.cursor(dictionary=True)
    
    print("=" * 80)
    print("Generating Slow Queries for Testing (REVIEWED VERSION)")
    print("=" * 80)
    print(f"Database: beer_reviews")
    print(f"Table: beer_reviews_flat (~2.9M rows)")
    print(f"Iterations per query: {num_iterations}")
    print(f"Total queries to run: {len(SAFE_SLOW_QUERIES) * num_iterations}")
    print(f"\n⚠️  REMOVED dangerous queries:")
    print(f"   - Self-join (would create massive cartesian product)")
    print(f"   - Cross-product JOIN (even worse)")
    print(f"   - Correlated subquery (runs subquery for every row)")
    print("=" * 80)
    print()
    
    results = []
    
    for query_info in SAFE_SLOW_QUERIES:
        query_name = query_info["name"]
        query = query_info["query"]
        why_slow = query_info.get("why_slow", "Complex query")
        
        print(f"\n{'='*80}")
        print(f"Query: {query_name}")
        print(f"Why slow: {why_slow}")
        print(f"{'='*80}")
        
        for iteration in range(1, num_iterations + 1):
            print(f"\n  Iteration {iteration}/{num_iterations}...", end=" ", flush=True)
            
            start_time = time.time()
            try:
                cursor.execute(query)
                rows = cursor.fetchall()
                execution_time = time.time() - start_time
                
                print(f"✓ Completed in {execution_time:.2f}s ({len(rows)} rows)")
                
                results.append({
                    "query_name": query_name,
                    "iteration": iteration,
                    "execution_time": execution_time,
                    "rows_returned": len(rows),
                    "status": "success"
                })
                
                # If query was fast, warn user
                if execution_time < 5.0:
                    print(f"    ⚠ Warning: Query completed in {execution_time:.2f}s (< 5s threshold)")
                
            except Exception as e:
                execution_time = time.time() - start_time
                print(f"✗ Failed after {execution_time:.2f}s: {str(e)}")
                
                results.append({
                    "query_name": query_name,
                    "iteration": iteration,
                    "execution_time": execution_time,
                    "rows_returned": 0,
                    "status": "error",
                    "error": str(e)
                })
    
    cursor.close()
    conn.close()
    
    # Print summary
    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)
    
    successful = [r for r in results if r["status"] == "success"]
    slow_queries = [r for r in successful if r["execution_time"] >= 5.0]
    
    print(f"Total queries run: {len(results)}")
    print(f"Successful: {len(successful)}")
    print(f"Failed: {len(results) - len(successful)}")
    print(f"Slow queries (>= 5s): {len(slow_queries)}")
    
    if slow_queries:
        print(f"\nAverage execution time for slow queries: {sum(r['execution_time'] for r in slow_queries) / len(slow_queries):.2f}s")
        print(f"Slowest query: {max(slow_queries, key=lambda x: x['execution_time'])['execution_time']:.2f}s")
    
    print("\n" + "=" * 80)
    print("Slow queries have been generated in the slow query log!")
    print("You can now run the slow query agent to analyze them:")
    print("  python -m mariadb_db_agents.cli.main slow-query --hours 1 --max-patterns 5")
    print("  OR")
    print("  python -m mariadb_db_agents.agents.slow_query.main --hours 1 --max-patterns 5")
    print("=" * 80)
    
    return results


if __name__ == "__main__":
    import sys
    
    num_iterations = 2
    if len(sys.argv) > 1:
        try:
            num_iterations = int(sys.argv[1])
        except ValueError:
            print("Usage: python generate_slow_queries_reviewed.py [num_iterations]")
            sys.exit(1)
    
    run_slow_queries(num_iterations)

