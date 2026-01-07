# Sample DBA Questions for MariaDB Database Management Agents

This document provides example questions that demonstrate the capabilities of the MariaDB Database Management Agents, especially for complex root cause analysis scenarios.

## Quick Health & Status Checks

**Simple questions that get you started:**

- "Is my database healthy?"
- "What's the current status of my database?"
- "Show me a quick health check"
- "Are there any immediate issues I should be aware of?"

## Performance Investigation

**Questions that require deep analysis across multiple dimensions:**

- "Why are my queries slow today compared to yesterday?"
- "What's causing high CPU usage on my database server?"
- "I'm seeing increased response times in my application. What queries are the bottleneck?"
- "Which queries are consuming the most resources right now?"
- "Analyze slow queries from the last 3 hours and identify the top 5 patterns causing performance degradation"

**Complex multi-part investigations:**

- "My application is experiencing timeouts. 
  Can you check if there are blocking queries, 
  analyze slow queries from the last hour, 
  and identify any connection issues?"

- "Users are reporting slow page loads. 
  Investigate what's happening: 
  check running queries, 
  analyze recent slow queries, 
  and see if there are any locks or resource contention issues."

- "Performance degraded after a recent deployment. 
  Compare slow queries from the last 24 hours 
  with the previous 24 hours and identify what changed."

## Root Cause Analysis

**Complex scenarios requiring multi-agent coordination:**

- "Something is wrong with my database. 
  The application is slow and I'm seeing errors. 
  Can you do a comprehensive investigation to find the root cause?"

- "My database suddenly became unresponsive. 
  Check for blocking queries, 
  analyze error logs, 
  review replication status, 
  and identify what might have caused this."

- "I'm seeing intermittent performance issues. 
  Investigate slow queries, 
  check for lock contention, 
  review connection pool usage, 
  and identify patterns that might explain the intermittent behavior."

- "After a recent schema change, queries are taking much longer. 
  Analyze slow queries, 
  check if indexes are being used properly, 
  and identify what optimization opportunities exist."

## Query Optimization

**Questions focused on improving query performance:**

- "What are the slowest queries in the last 24 hours and how can I optimize them?"
- "Which queries would benefit most from adding indexes?"
- "Are there any queries using full table scans that could be optimized?"
- "Find queries that are doing LIKE searches on large text columns and suggest fulltext index optimizations"
- "Analyze slow queries and suggest query rewrites that would improve performance"

**Complex optimization scenarios:**

- "I have a query that's taking 30 seconds. 
  Can you analyze it, 
  check the execution plan, 
  review table structure and indexes, 
  and provide specific recommendations to optimize it?"

- "Our reporting queries are slow. 
  Analyze slow queries from the last week, 
  identify patterns, 
  and suggest indexes or query rewrites that would help."

## Replication & High Availability

**Questions about replication health and lag:**

- "Is replication healthy across all replicas?"
- "Check replication lag and identify any replicas that are falling behind"
- "Why is replication lagging on one of my replicas?"
- "Are there any replication failures I should be aware of?"

**Complex replication scenarios:**

- "After a network issue, replication seems off. 
  Check the replication status across all replicas, 
  identify any failures or lag, 
  and provide recommendations for recovery."

- "I'm planning a failover. 
  Check replication health, 
  verify lag is acceptable, 
  and confirm all replicas are in sync."

## Connection & Resource Management

**Questions about connections and resource usage:**

- "How many connections are currently active?"
- "Are there connection leaks or too many idle connections?"
- "What's the connection pool utilization?"
- "Check for long-running connections that might be holding resources"

**Complex resource investigation:**

- "My database is running out of connections. 
  Investigate active connections, 
  identify any connection leaks, 
  check for long-running queries holding connections, 
  and suggest solutions."

## Incident Triage & Troubleshooting

**Questions for when something is wrong:**

- "Something's wrong with my database. Where do I start?"
- "I'm seeing errors in my application logs. Can you check the database error logs?"
- "The database seems unresponsive. Do a quick triage to identify the issue."
- "After a recent change, the database is behaving strangely. Investigate what might be wrong."

**Complex incident scenarios:**

- "We had a brief outage. 
  Check error logs, 
  analyze what queries were running during that time, 
  review replication status, 
  and help me understand what happened."

- "Users are reporting data inconsistencies. 
  Check replication status, 
  review error logs, 
  and identify if there are any replication issues that could explain this."

## Capacity Planning & Trends

**Questions about resource usage and trends:**

- "Is my database approaching any resource limits?"
- "What's the trend in slow queries over the last week?"
- "Are there any queries that are getting slower over time?"
- "Check if we're approaching connection limits or other resource constraints"

## Schema & Index Analysis

**Questions about database structure and optimization:**

- "Are there any unused indexes that could be removed?"
- "Which tables would benefit from additional indexes?"
- "Check if my indexes are being used effectively"
- "Analyze table structures and suggest schema optimizations"

**Complex schema investigation:**

- "After adding a new index, queries are still slow. 
  Check if the index is being used, 
  analyze query execution plans, 
  and identify why the index isn't helping."

## Multi-Database & Environment Analysis

**Questions for complex environments:**

- "Compare performance between my production and staging databases"
- "Check replication lag across all environments"
- "Are there any differences in slow query patterns between environments?"

## Real-Time Monitoring

**Questions about current database state:**

- "What queries are running right now?"
- "Are there any blocking queries I should be aware of?"
- "Show me queries that have been running for more than 5 seconds"
- "What's the current database load and what's causing it?"

**Complex real-time investigation:**

- "I'm seeing high CPU usage right now. 
  Check what queries are currently running, 
  identify any blocking queries, 
  and see if there are any long-running operations causing the issue."

## Post-Deployment Verification

**Questions after making changes:**

- "I just deployed a new version. Check if database performance is normal"
- "After a schema change, verify that queries are performing as expected"
- "Check if the recent index addition is being used and improving performance"

## Best Practices & Recommendations

**Questions seeking general guidance:**

- "What are the top optimization opportunities in my database?"
- "Review my database configuration and suggest improvements"
- "What are the most impactful changes I could make to improve performance?"
- "Provide a prioritized list of database optimizations I should consider"

## Advanced Multi-Agent Scenarios

**Complex questions that require the Orchestrator to coordinate multiple agents:**

- "My application performance has degraded over the last week. 
  Do a comprehensive analysis: 
  check current running queries, 
  analyze slow queries from the last 7 days, 
  review error logs, 
  check replication health, 
  and provide a prioritized list of issues to address."

- "We're planning a major release. 
  Perform a full health check: 
  verify database health, 
  check for any existing performance issues, 
  review replication status, 
  and confirm we're ready for the release."

- "I suspect there's a query causing problems but I'm not sure which one. 
  Investigate: 
  check for blocking queries, 
  analyze slow queries, 
  review connection usage, 
  and help me identify the culprit."

- "After a recent migration, performance is inconsistent. 
  Investigate: 
  compare slow queries before and after, 
  check for new blocking patterns, 
  review replication lag, 
  and identify what might be causing the inconsistency."

## Tips for Getting the Best Results

1. **Be specific about timeframes**: "last hour", "last 24 hours", "since yesterday"
2. **Mention symptoms**: "slow", "timeouts", "errors", "high CPU"
3. **Include context**: "after deployment", "during peak hours", "after schema change"
4. **Ask for prioritization**: "top 5", "most impactful", "highest priority"
5. **Request follow-up**: "Can you explain why?", "What would help optimize this?"

## Using the Orchestrator

The **Orchestrator** is designed to handle all these questions intelligently. It will:
- Route to the appropriate specialized agents
- Coordinate multiple agents when needed
- Synthesize results into actionable reports
- Maintain context across follow-up questions

Simply ask your question naturally - the Orchestrator will figure out which agents to use and how to combine their insights.

