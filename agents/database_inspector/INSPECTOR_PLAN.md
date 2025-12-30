# Database Inspector Agent - Plan

## Problem Statement

Current agents (Slow Query, Running Query, Incident Triage, Replication Health) often recommend that users:
- Execute SQL queries on `information_schema` tables
- Check `GLOBAL_STATUS` or `GLOBAL_VARIABLES`
- Query `performance_schema` tables
- Run `SHOW` commands
- Investigate specific tables or metrics

However, the Orchestrator cannot easily follow up on these recommendations. Users have to manually execute these queries, which breaks the workflow.

## Solution: Database Inspector Agent

A general-purpose agent that can execute read-only SQL queries and provide formatted results. This allows the Orchestrator to:
1. Follow up on recommendations from other agents
2. Investigate issues by querying the database directly
3. Provide interactive database exploration capabilities

## Agent Capabilities

### Core Functionality
- Execute read-only SQL queries safely
- Query `information_schema` tables (processlist, tables, columns, etc.)
- Query `GLOBAL_STATUS` and `GLOBAL_VARIABLES`
- Query `performance_schema` tables (if available)
- Execute `SHOW` commands (SHOW STATUS, SHOW VARIABLES, SHOW PROCESSLIST, etc.)
- Format and present results clearly
- Handle errors gracefully

### Safety Features
- **Read-only enforcement**: Only allows SELECT, SHOW, DESCRIBE, EXPLAIN queries
- **Query validation**: Rejects DDL, DML, DCL statements
- **Result limits**: Limits result sets to prevent overwhelming output
- **Timeout protection**: Prevents long-running queries from hanging

### Use Cases

1. **Follow-up on Agent Recommendations**
   - Agent says "Check `information_schema.processlist` for long-running queries"
   - Orchestrator can use Inspector Agent to execute: `SELECT * FROM information_schema.processlist WHERE time > 60`
   - Results are formatted and presented to user

2. **Interactive Investigation**
   - User asks: "What tables are in the database?"
   - Orchestrator uses Inspector Agent: `SELECT table_name, table_rows FROM information_schema.tables WHERE table_schema = 'mydb'`

3. **Status/Variable Checks**
   - Agent recommends: "Check `max_connections` setting"
   - Orchestrator uses Inspector Agent: `SHOW VARIABLES LIKE 'max_connections'`

4. **Performance Schema Analysis**
   - Agent recommends: "Check statement analysis"
   - Orchestrator uses Inspector Agent: `SELECT * FROM performance_schema.events_statements_summary_by_digest ORDER BY sum_timer_wait DESC LIMIT 10`

## Implementation Plan

### Phase 1: Core Agent (Basic SQL Execution)
- Tool: `execute_sql()` - Execute read-only SQL queries
- System prompt: Instructions for safe SQL execution
- Result formatting: Clean, readable output
- Error handling: Graceful error messages

### Phase 2: Enhanced Features (Optional Future Enhancements)
- Result formatting improvements: Better table formatting, summary statistics
- Query validation enhancements: Better error messages, query optimization hints
- Common query shortcuts: Pre-built queries for common tasks (optional)

### Phase 3: Integration
- Add to Orchestrator tools
- Update Orchestrator prompt to use Inspector Agent for follow-ups
- Add examples in documentation

## Tool Design

### Tool: execute_sql

```python
@function_tool
def execute_sql(
    sql: str,
    max_rows: int = 100,
    timeout_seconds: int = 10,
    database: str | None = None,
    format_output: bool = True,
) -> dict[str, Any]:
    """
    Execute a read-only SQL query against the database.
    
    Use this to:
    - Query information_schema tables
    - Check GLOBAL_STATUS and GLOBAL_VARIABLES
    - Query performance_schema tables
    - Execute SHOW commands
    - Investigate specific tables or metrics
    
    Args:
        sql: Read-only SQL statement (SELECT, SHOW, DESCRIBE, EXPLAIN)
        max_rows: Maximum number of rows to return (default: 100)
        timeout_seconds: Query timeout in seconds (default: 10)
        database: Optional database name to use
        format_output: Whether to format output for readability (default: True)
    
    Returns:
        Dictionary with:
        - 'rows': Query results (list of dictionaries)
        - 'row_count': Number of rows returned
        - 'columns': Column names
        - 'execution_time': Query execution time in seconds
        - 'note': Additional information or warnings
    """
```

## System Prompt Outline

```
You are a MariaDB Database Inspector - a general-purpose SQL query agent.

Your job:
- Execute read-only SQL queries safely
- Query information_schema, performance_schema, and other system tables
- Execute SHOW commands
- Format and present results clearly
- Provide insights based on query results

Safety Rules:
- ONLY execute read-only queries (SELECT, SHOW, DESCRIBE, EXPLAIN)
- NEVER execute DDL, DML, or DCL statements
- Always use query timeouts
- Limit result sets to prevent overwhelming output

Use Cases:
1. Follow-up on recommendations from other agents
2. Investigate database state
3. Check configuration and status
4. Explore database schema

Output Format:
- Present results in clear, readable format
- Highlight important values
- Provide context and interpretation when helpful
```

## Integration with Orchestrator

### Orchestrator Tool

```python
@function_tool
async def execute_database_query(
    sql: str,
    max_rows: int = 100,
    timeout_seconds: int = 10,
) -> dict[str, Any]:
    """
    Execute a read-only SQL query using the Database Inspector Agent.
    
    Use this to execute SQL queries recommended by other agents or requested by users.
    Supports SELECT, SHOW, DESCRIBE, EXPLAIN statements on information_schema,
    performance_schema, GLOBAL_STATUS, GLOBAL_VARIABLES, and user tables.
    
    Args:
        sql: Read-only SQL statement to execute
        max_rows: Maximum rows to return (default: 100)
        timeout_seconds: Query timeout (default: 10)
    
    Returns:
        Dictionary with query results and metadata
    """
```

### Orchestrator Prompt Update

Simply add to the "Available Specialized Agents" section:
- **Database Inspector Agent** (execute_database_query)
  - Purpose: Execute read-only SQL queries to investigate database state, check status/variables, explore schema
  - Use when: Other agents recommend SQL queries, user asks to check specific data, need to follow up on recommendations
  - Parameters: sql (query to execute), max_rows (default: 100), timeout_seconds (default: 10)

## Example Use Cases

- Follow-up on agent recommendations: When an agent suggests "Check information_schema.processlist", orchestrator can execute it automatically
- Interactive queries: User asks "What tables are in my database?" → orchestrator executes and presents results
- Status checks: Check GLOBAL_STATUS, GLOBAL_VARIABLES, SHOW commands
- Schema exploration: Query information_schema to understand database structure

## Benefits

1. **Seamless Workflow**: Orchestrator can follow up on recommendations automatically
2. **Interactive**: Users can ask questions and get immediate answers
3. **Safe**: Read-only enforcement prevents accidental changes
4. **Flexible**: Can query any read-only data source
5. **Integrated**: Works seamlessly with other agents

## Considerations

1. **Security**: Must enforce read-only strictly
2. **Performance**: Limit result sets and timeouts
3. **Error Handling**: Graceful handling of permission errors, missing tables, etc.
4. **Result Formatting**: Present large result sets clearly
5. **Context**: Agent should understand what it's querying and provide context

## Next Steps

1. Review and approve this plan
2. Implement Phase 1 (core agent)
3. Test with orchestrator integration
4. Add to documentation
5. Iterate based on feedback

