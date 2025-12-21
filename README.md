# MariaDB Database Management Agents

AI-powered agents using **OpenAI Agents SDK** and Python for analyzing and optimizing MariaDB databases.

## Overview

This project is a comprehensive platform for MariaDB database management with specialized AI agents for different aspects of database analysis and optimization:

1. **Slow Query Agent**: Analyzes historical slow queries from slow query logs
2. **Running Query Agent**: Analyzes currently executing SQL queries in real-time
3. **More agents coming soon**: Replication health, connection pool management, capacity planning, and more

All agents use the **OpenAI Agents SDK** to intelligently query the database and provide actionable recommendations.

### Key Features

- **Multi-Agent Platform**: Extensible architecture for adding new specialized agents
- **Built with OpenAI Agents SDK**: Uses the official `openai-agents` package with proper tool integration
- **Guardrails**: Input and output guardrails for safety and validation
- **Read-only Operations**: All database operations are read-only for safety
- **Intelligent Analysis**: Automatically discovers configurations, aggregates patterns, and provides recommendations
- **Performance Schema Integration**: Advanced performance metrics including CPU time, lock wait time, I/O statistics, and buffer pool analysis
- **Deep Query Analysis**: Comprehensive EXPLAIN plan analysis, table/index inspection, and query rewrite suggestions
- **Fulltext Index Detection**: Automatically detects fulltext indexes and suggests MATCH...AGAINST rewrites for LIKE queries
- **Query Categorization**: Identifies CPU-bound, I/O-bound, and lock-bound queries for targeted optimization
- **Unified CLI**: Single command-line interface for all agents
- **Interactive Mode**: Conversation-based interaction with agents

## Project Structure

```
mariadb_db_agents/
├── agents/                      # Specialized agents
│   ├── slow_query/              # Slow query analysis agent
│   │   ├── agent.py             # Agent definition
│   │   ├── tools.py             # Agent-specific tools
│   │   ├── main.py              # CLI entry point
│   │   └── conversation.py      # Interactive mode
│   │
│   ├── running_query/           # Running query analysis agent
│   │   ├── agent.py
│   │   ├── tools.py
│   │   ├── main.py
│   │   └── conversation.py
│   │
│   └── ...                      # Future agents
│
├── common/                      # Shared infrastructure
│   ├── config.py                # Configuration management
│   ├── db_client.py             # Database client
│   ├── guardrails.py            # Safety guardrails
│   ├── observability.py         # Metrics tracking
│   ├── performance_metrics.py   # Performance Schema helpers
│   └── performance_tools.py     # Performance Schema tools
│
├── cli/                         # Unified CLI interface
│   └── main.py                  # Main entry point
│
├── orchestrator/                # Future: DBA orchestrator agent
│
├── scripts/                     # Utility scripts
│   ├── generate_slow_queries.py
│   └── ...
│
├── docs/                        # Documentation
│   ├── HIGH_VALUE_AUTOMATION_OPPORTUNITIES.md
│   └── ...
│
├── tests/                       # Test suite
│
├── requirements.txt             # Dependencies
├── .env.example                 # Environment template
├── enable_performance_schema.sql
└── README.md
```

## Setup

### 1. Activate Virtual Environment

The parent directory (`python_programs`) has a virtual environment with all required dependencies. Activate it:

```bash
cd /Users/jagsramnarayan-mariadb/Documents/skysql/develop/python_programs
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
```

### 2. Install Dependencies

```bash
pip install -r mariadb_db_agents/requirements.txt
```

This will install:
- `openai-agents` - The OpenAI Agents SDK
- `mysql-connector-python` - MariaDB/MySQL connector
- `python-dotenv` - Environment variable management

### 3. Configure Environment

Copy `.env.example` to `.env` and fill in your credentials:

```bash
cd mariadb_db_agents
cp .env.example .env
```

Edit `.env` with your actual values:
- `OPENAI_API_KEY`: Your OpenAI API key
- `OPENAI_MODEL`: Model to use (default: `gpt-4o-mini`)
- `DB_HOST`: MariaDB host address
- `DB_PORT`: MariaDB port (default: 3306)
- `DB_USER`: Read-only database user
- `DB_PASSWORD`: Database password
- `DB_DATABASE`: Database name

**Note**: Database connections are configured via environment variables (DB_HOST, DB_PORT, DB_USER, DB_PASSWORD, DB_DATABASE).

## Usage

### Unified CLI (Recommended)

Use the unified CLI to access all agents:

```bash
# Analyze slow queries
python -m mariadb_db_agents.cli.main slow-query --hours 1 --max-patterns 5

# Analyze running queries
python -m mariadb_db_agents.cli.main running-query --min-time-seconds 5.0

# Interactive conversation mode
python -m mariadb_db_agents.cli.main slow-query --interactive
python -m mariadb_db_agents.cli.main running-query --interactive
```

### Individual Agent Entry Points

You can also run agents directly:

#### Slow Query Agent

```bash
# CLI mode
python -m mariadb_db_agents.agents.slow_query.main --hours 1 --max-patterns 5

# Interactive mode
python -m mariadb_db_agents.agents.slow_query.conversation
```

**Arguments:**
- `--hours` (optional, default: 1.0): Time window in hours to analyze slow queries
- `--max-patterns` (optional, default: 8): Maximum number of query patterns to deep-analyze

**Note**: Database connection is configured via environment variables (DB_HOST, DB_PORT, DB_USER, DB_PASSWORD, DB_DATABASE).

#### Running Query Agent

```bash
# CLI mode
python -m mariadb_db_agents.agents.running_query.main --min-time-seconds 1.0

# Interactive mode
python -m mariadb_db_agents.agents.running_query.conversation
```

**Arguments:**
- `--min-time-seconds` (optional, default: 1.0): Minimum query execution time in seconds to analyze
- `--include-sleeping` (optional): Include sleeping/idle connections in the analysis
- `--max-queries` (optional, default: 20): Maximum number of queries to analyze in detail

**Note**: Database connection is configured via environment variables (DB_HOST, DB_PORT, DB_USER, DB_PASSWORD, DB_DATABASE).

### Interactive Conversation Mode

Both agents support interactive conversation mode where you can:
- Ask follow-up questions
- Request deeper analysis of specific queries
- Get clarification on recommendations
- Explore different time windows or query patterns

**Commands:**
- `help` - Show available commands
- `clear` - Clear conversation history
- `stats` - Show observability statistics (token usage, round trips)
- `quit` or `exit` - End the conversation

**Example conversation:**
```
You: Analyze slow queries from the last hour
Agent: [Provides analysis...]

You: Can you explain why the first query is so slow?
Agent: [Explains the query pattern...]

You: What index would help optimize it?
Agent: [Suggests specific indexes...]
```

## Differences Between Agents

| Aspect | Slow Query Agent | Running Query Agent |
|--------|------------------|---------------------|
| **Data Source** | `mysql.slow_log` (historical) | `information_schema.processlist` (real-time) |
| **Time Window** | Hours/days in past | Current moment snapshot |
| **Focus** | Optimization, indexing, patterns | Blocking, resource usage, immediate issues |
| **Analysis** | Aggregation, patterns, query rewrites | Individual queries, locks, waits, real-time metrics |
| **Performance Metrics** | Aggregated by query digest | Per-thread metrics (current CPU time, lock wait) |
| **Use Case** | Long-term optimization | Real-time troubleshooting |

## How It Works

### Slow Query Agent

1. **Configuration Discovery**: Checks if slow query logging is enabled and where logs are stored
2. **Query Retrieval**: Aggregates slow queries from `mysql.slow_log` table or slow query log file
3. **Pattern Analysis**: Identifies top query patterns by total execution time, execution count, and impact
4. **Performance Schema Analysis**: Retrieves aggregated metrics (CPU time, lock wait time, I/O statistics)
5. **Deep Analysis**: Runs `EXPLAIN FORMAT=JSON`, inspects schemas/indexes, analyzes query rewrites
6. **Recommendations**: Provides prioritized suggestions (query rewrites, indexes, configuration)

### Running Query Agent

1. **Process List Retrieval**: Queries `information_schema.processlist` to get currently executing queries
2. **Problem Identification**: Identifies long-running queries, blocking queries, and queries in problematic states
3. **Performance Schema Analysis**: Retrieves real-time metrics per thread
4. **Lock Analysis**: Checks for blocking relationships
5. **Deep Query Analysis**: Runs `EXPLAIN FORMAT=JSON`, inspects schemas/indexes
6. **Recommendations**: Provides suggestions for killing queries, query rewrites, resource management

## Performance Schema Integration

Both agents leverage MariaDB's Performance Schema for advanced performance analysis when available. The agents gracefully degrade if Performance Schema is not enabled.

See `enable_performance_schema.sql` for setup instructions.

## Architecture

**Shared Components (`common/`):**
- **`config.py`**: Manages OpenAI API and database configuration
- **`db_client.py`**: Provides read-only database operations with safety checks
- **`guardrails.py`**: Implements input/output guardrails
- **`observability.py`**: Tracks LLM usage metrics (tokens, round trips)
- **`performance_metrics.py`**: Data structures and helper functions for Performance Schema
- **`performance_tools.py`**: Tools for querying Performance Schema

**Agent Structure:**
Each agent follows a consistent structure:
- **`agent.py`**: Creates the agent instance with tools, guardrails, and system prompt
- **`tools.py`**: Defines agent-specific tools using `@function_tool` decorator
- **`main.py`**: CLI entry point for one-time analysis
- **`conversation.py`**: Interactive conversation client

## Future Enhancements

See `docs/HIGH_VALUE_AUTOMATION_OPPORTUNITIES.md` for a comprehensive list of planned agents and features.

Upcoming agents:
- **Replication Health Agent**: Monitor replication lag and health
- **Connection Pool Agent**: Analyze connection usage and leaks
- **Capacity Planning Agent**: Predict resource exhaustion
- **Schema Health Agent**: Identify unused indexes and optimization opportunities
- **Security Audit Agent**: Audit permissions and security
- **DBA Orchestrator**: Routes queries to appropriate specialized agents

## Contributing

This is a multi-agent platform designed for extensibility. To add a new agent:

1. Create a new directory under `agents/`
2. Follow the structure of existing agents
3. Implement `agent.py`, `tools.py`, `main.py`, and `conversation.py`
4. Add the agent to the unified CLI in `cli/main.py`
5. Update this README

## Observability

The agents include built-in observability tracking for LLM usage:
- Token usage (input, output, total)
- Round trips (number of API calls)
- Per-request breakdown
- Context size

Metrics are automatically logged to `.observability_log.json` and displayed in interactive mode.

## Notes

- All agents only execute read-only SQL queries for safety
- All DDL and configuration changes are presented as suggestions only
- Agents apply guardrails to limit analysis scope
- Input guardrails prevent dangerous SQL injection attempts
- Output guardrails prevent leaking sensitive information
- Agents use async/await patterns as required by the SDK

## License

[Add your license here]

## Support

[Add support information here]

