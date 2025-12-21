#!/usr/bin/env python3
"""
Generate slow queries on beer_reviews database for testing the slow query agent.

This script runs complex queries that will take >5 seconds to execute,
generating entries in the slow query log.
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

# Complex queries designed to be slow (>5 seconds)
SLOW_QUERIES = [
    {
        "name": "Full table scan with text search",
        "query": """
            SELECT beer_name, beer_style, review_text, review_overall
            FROM beer_reviews_flat
            WHERE review_text LIKE '%delicious%'
               OR review_text LIKE '%excellent%'
               OR review_text LIKE '%amazing%'
            ORDER BY review_time DESC
            LIMIT 1000
        """
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
        """
    },
    {
        "name": "Self-join for finding similar beers",
        "query": """
            SELECT 
                b1.beer_name as beer1,
                b2.beer_name as beer2,
                b1.beer_style,
                COUNT(*) as common_reviewers
            FROM beer_reviews_flat b1
            JOIN beer_reviews_flat b2 
                ON b1.review_profileName = b2.review_profileName
                AND b1.beer_beerId < b2.beer_beerId
            WHERE b1.beer_style = b2.beer_style
            GROUP BY b1.beer_name, b2.beer_name, b1.beer_style
            HAVING common_reviewers > 5
            ORDER BY common_reviewers DESC
            LIMIT 100
        """
    },
    {
        "name": "Complex text search with multiple conditions",
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
        """
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
        """
    },
    {
        "name": "Cross-product style comparison",
        "query": """
            SELECT 
                s1.beer_style as style1,
                s2.beer_style as style2,
                AVG(CAST(s1.review_overall AS DECIMAL(5,2))) as avg_style1,
                AVG(CAST(s2.review_overall AS DECIMAL(5,2))) as avg_style2,
                COUNT(DISTINCT s1.review_profileName) as reviewers_style1,
                COUNT(DISTINCT s2.review_profileName) as reviewers_style2
            FROM beer_reviews_flat s1
            CROSS JOIN beer_reviews_flat s2
            WHERE s1.beer_style < s2.beer_style
              AND s1.review_time >= DATE_SUB(NOW(), INTERVAL 2 YEAR)
              AND s2.review_time >= DATE_SUB(NOW(), INTERVAL 2 YEAR)
            GROUP BY s1.beer_style, s2.beer_style
            HAVING reviewers_style1 > 100 AND reviewers_style2 > 100
            ORDER BY (avg_style1 + avg_style2) DESC
            LIMIT 50
        """
    },
    {
        "name": "Complex date range with text analysis",
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
        """
    },
    {
        "name": "Subquery with correlated conditions",
        "query": """
            SELECT 
                beer_name,
                beer_style,
                review_overall,
                review_time,
                (SELECT COUNT(*) 
                 FROM beer_reviews_flat b2 
                 WHERE b2.beer_style = b1.beer_style 
                   AND CAST(b2.review_overall AS DECIMAL(5,2)) > CAST(b1.review_overall AS DECIMAL(5,2))
                ) as better_reviews_count,
                (SELECT AVG(CAST(review_overall AS DECIMAL(5,2)))
                 FROM beer_reviews_flat b3
                 WHERE b3.beer_beerId = b1.beer_beerId
                ) as beer_avg_rating
            FROM beer_reviews_flat b1
            WHERE review_time >= DATE_SUB(NOW(), INTERVAL 1 YEAR)
            ORDER BY CAST(review_overall AS DECIMAL(5,2)) DESC
            LIMIT 1000
        """
    }
]


def run_slow_queries(num_iterations=3):
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
        database='beer_reviews',  # Use beer_reviews database
        ssl_disabled=True,
        connection_timeout=30,
    )
    
    cursor = conn.cursor(dictionary=True)
    
    print("=" * 80)
    print("Generating Slow Queries for Testing")
    print("=" * 80)
    print(f"Database: beer_reviews")
    print(f"Table: beer_reviews_flat (~2.9M rows)")
    print(f"Iterations per query: {num_iterations}")
    print(f"Total queries to run: {len(SLOW_QUERIES) * num_iterations}")
    print("=" * 80)
    print()
    
    results = []
    
    for query_info in SLOW_QUERIES:
        query_name = query_info["name"]
        query = query_info["query"]
        
        print(f"\n{'='*80}")
        print(f"Query: {query_name}")
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
    
    num_iterations = 3
    if len(sys.argv) > 1:
        try:
            num_iterations = int(sys.argv[1])
        except ValueError:
            print("Usage: python generate_slow_queries.py [num_iterations]")
            sys.exit(1)
    
    run_slow_queries(num_iterations)

