# MariaDB Database Management Agents

AI-powered agents using **OpenAI Agents SDK** and Python for analyzing and optimizing MariaDB databases.

## Overview

This project is a comprehensive platform for MariaDB database management with specialized AI agents for different aspects of database analysis and optimization:

1. **Slow Query Agent**: Analyzes historical slow queries from slow query logs
2. **Running Query Agent**: Analyzes currently executing SQL queries in real-time
3. **Incident Triage Agent**: Quick health check that identifies database issues and provides actionable checklists
4. **DBA Orchestrator**: Meta-agent that intelligently routes queries to specialized agents and synthesizes comprehensive reports
5. **Replication Health Agent**: Monitors replication lag, detects failures, and recommends optimizations
6. **Database Inspector Agent**: Executes read-only SQL queries for follow-up analysis and interactive investigation
7. **More agents coming soon**: Connection pool management, capacity planning, lock & deadlock detection, and more

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
- **DBA Orchestrator**: Intelligent routing to specialized agents based on user queries
- **SkySQL Integration**: Error log access via SkySQL API
- **SkySQL Observability**: CPU% and disk utilization metrics via SkySQL Observability API (not accessible via SQL)
- **Error Log Analysis**: Pattern extraction and analysis from database error logs (supports local files and SkySQL API)
- **Slow Log File Support**: Read slow query logs from local files or mysql.slow_log table
- **Replication Monitoring**: Monitor replication lag, detect failures, and analyze replication health
- **Database Inspector**: Execute read-only SQL queries for interactive investigation and follow-up analysis
- **LLM Usage Telemetry**: Comprehensive tracking and aggregation of token usage across orchestrator and sub-agents

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
│   ├── incident_triage/         # Incident triage agent
│   │   ├── agent.py
│   │   ├── tools.py
│   │   └── main.py
│   │
│   ├── replication_health/      # Replication health agent
│   │   ├── agent.py
│   │   ├── tools.py
│   │   └── main.py
│   │
│   ├── database_inspector/      # Database inspector agent
│   │   ├── agent.py
│   │   ├── tools.py
│   │   └── main.py
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
├── orchestrator/                # DBA orchestrator agent
│   ├── agent.py                 # Orchestrator agent definition
│   ├── tools.py                 # Tools for invoking other agents
│   ├── main.py                  # CLI entry point
│   ├── conversation.py          # Interactive conversation mode
│   ├── README.md                # Orchestrator usage guide
│   ├── ORCHESTRATOR_PLAN.md     # Implementation plan
│   └── ADVANCED_WORKFLOWS.md    # Advanced multi-agent workflows
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

## Installation

### Option 1: Install from Git Repository

```bash
# Clone the repository
git clone https://github.com/mariadb-JagsR/mariadb-db-agents.git
cd mariadb-db-agents

# Create and activate virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install in development mode
pip install -e .

# Or install dependencies directly
pip install -r requirements.txt
```

### Option 2: Use Existing Virtual Environment

If you have an existing virtual environment with dependencies:

```bash
# Activate your virtual environment
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -r mariadb_db_agents/requirements.txt
```

### Dependencies

This will install:
- `openai-agents` - The OpenAI Agents SDK
- `mysql-connector-python` - MariaDB/MySQL connector
- `python-dotenv` - Environment variable management
- `requests` - HTTP requests for SkySQL API integration
- `python-dateutil` - Date parsing for log analysis

### 3. Configure Environment

Copy `.env.example` to `.env` and fill in your credentials:

```bash
cd mariadb_db_agents
cp .env.example .env
```

Edit `.env` with your actual values:
- `OPENAI_API_KEY`: Your OpenAI API key
- `OPENAI_MODEL`: Model to use (default: `gpt-5.2`)
- `DB_HOST`: MariaDB host address
- `DB_PORT`: MariaDB port (default: 3306)
- `DB_USER`: Read-only database user
- `DB_PASSWORD`: Database password
- `DB_DATABASE`: Database name
- `SKYSQL_API_KEY`: (Optional) SkySQL API key for error log access and observability metrics
- `SKYSQL_SERVICE_ID`: (Optional) SkySQL service ID for error log access and observability metrics
- `SKYSQL_LOG_API_URL`: (Optional) SkySQL log API URL (defaults to public API: `https://api.skysql.com/observability/v2/logs`)

**Note**: Database connections are configured via environment variables (DB_HOST, DB_PORT, DB_USER, DB_PASSWORD, DB_DATABASE).

## Usage

### Unified CLI (Recommended)

Use the unified CLI to access all agents:

```bash
# Analyze slow queries
python -m mariadb_db_agents.cli.main slow-query --hours 1 --max-patterns 5

# Analyze slow queries from a log file
python -m mariadb_db_agents.cli.main slow-query --slow-log-path /var/log/mysql/slow.log

# Analyze running queries
python -m mariadb_db_agents.cli.main running-query --min-time-seconds 5.0

# Perform incident triage
python -m mariadb_db_agents.cli.main incident-triage

# Perform incident triage with error log file
python -m mariadb_db_agents.cli.main incident-triage --error-log-path /var/log/mysql/error.log

# Check replication health
python -m mariadb_db_agents.cli.main replication-health

# Execute a database query
python -m mariadb_db_agents.cli.main inspector "SELECT * FROM information_schema.tables LIMIT 10"

# Use orchestrator (intelligent routing to specialized agents)
python -m mariadb_db_agents.cli.main orchestrator "Is my database healthy?"
python -m mariadb_db_agents.cli.main orchestrator "Analyze slow queries from the last hour"
python -m mariadb_db_agents.cli.main orchestrator --interactive

# Interactive conversation mode
python -m mariadb_db_agents.cli.main slow-query --interactive
python -m mariadb_db_agents.cli.main running-query --interactive
python -m mariadb_db_agents.cli.main orchestrator --interactive
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
- `--slow-log-path` (optional): Path to slow query log file. If provided, reads from file instead of mysql.slow_log table

**Note**: Database connection is configured via environment variables (DB_HOST, DB_PORT, DB_USER, DB_PASSWORD, DB_DATABASE). The agent prefers reading from mysql.slow_log table, but can read from a local file if `--slow-log-path` is provided.

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

#### Incident Triage Agent

```bash
# CLI mode
python -m mariadb_db_agents.cli.main incident-triage

# With error log path (local file)
python -m mariadb_db_agents.cli.main incident-triage --error-log-path /var/log/mysql/error.log

# With SkySQL service ID (API access)
python -m mariadb_db_agents.cli.main incident-triage --service-id YOUR_SERVICE_ID
```

**Arguments:**
- `--error-log-path` (optional): Path to error log file for local file access
- `--service-id` (optional): SkySQL service ID for API-based error log access
- `--max-error-patterns` (optional, default: 20): Maximum number of error patterns to extract
- `--error-log-lines` (optional, default: 5000): Number of lines to read from error log tail
- `--max-turns` (optional, default: 30): Maximum number of agent turns/tool calls

#### Replication Health Agent

```bash
# Check replication health
python -m mariadb_db_agents.cli.main replication-health

# With custom parameters
python -m mariadb_db_agents.cli.main replication-health --max-executions 10 --max-turns 20
```

**Arguments:**
- `--max-executions` (optional, default: 10): Number of times to execute SHOW ALL SLAVES STATUS to gather replica information
- `--max-turns` (optional, default: 20): Maximum number of agent turns/tool calls

**Note**: Works with SkySQL/MaxScale environments. Automatically detects master vs replica connections and gathers status from all replicas.

#### Database Inspector Agent

```bash
# Execute a SQL query
python -m mariadb_db_agents.cli.main inspector "SELECT VERSION()"

# Ask a question about the database
python -m mariadb_db_agents.cli.main inspector "What tables are in the database?"

# With custom parameters
python -m mariadb_db_agents.cli.main inspector "SELECT * FROM information_schema.tables" --max-rows 50 --timeout 15
```

**Arguments:**
- `query` (required): SQL query to execute or question about the database
- `--max-rows` (optional, default: 100): Maximum number of rows to return
- `--timeout` (optional, default: 10): Query timeout in seconds
- `--max-turns` (optional, default: 10): Maximum number of agent turns/tool calls

**Note**: Executes read-only queries only (SELECT, SHOW, DESCRIBE, EXPLAIN). Useful for follow-up analysis after other agents provide recommendations.

#### DBA Orchestrator

```bash
# One-shot query
python -m mariadb_db_agents.cli.main orchestrator "Is my database healthy?"

# With query parameter
python -m mariadb_db_agents.cli.main orchestrator 'Analyze slow queries from the last hour'

# Interactive conversation mode (recommended for multiple questions)
python -m mariadb_db_agents.cli.main orchestrator --interactive
```

**Arguments:**
- `query` (optional): User query about database management. If not provided, will prompt interactively (unless `--interactive` is used)
- `--max-turns` (optional, default: 30): Maximum number of agent turns/tool calls
- `--interactive`: Start interactive conversation mode

**Routing Logic:**
The orchestrator intelligently routes queries to appropriate specialized agents:
- **"slow queries"** / **"query performance"** → Routes directly to Slow Query Agent
- **"running queries"** / **"current queries"** → Routes directly to Running Query Agent
- **"replication"** / **"replica lag"** → Routes directly to Replication Health Agent
- **"execute SQL"** / **"query database"** → Routes directly to Database Inspector Agent
- **"health check"** / **"is my database healthy?"** → Routes to Incident Triage Agent
- **"why is it slow?"** → Routes based on findings (may use multiple agents)
- **Unclear queries** → Asks for clarification instead of defaulting to Incident Triage

**Note:** The orchestrator is designed to route directly to specific agents when appropriate, avoiding unnecessary calls to the expensive Incident Triage Agent.

### Interactive Conversation Mode

All agents support interactive conversation mode where you can:
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

| Aspect | Slow Query Agent | Running Query Agent | Incident Triage Agent | Replication Health | Database Inspector | Orchestrator |
|--------|------------------|---------------------|---------------------|-------------------|-------------------|--------------|
| **Data Source** | `mysql.slow_log` or log file (historical) | `information_schema.processlist` (real-time) | Health metrics, error logs | Replication status, lag metrics | Any read-only SQL | Routes to other agents |
| **Time Window** | Hours/days in past | Current moment snapshot | Current snapshot | Current + trends | N/A | N/A (meta-agent) |
| **Focus** | Optimization, indexing, patterns | Blocking, resource usage, immediate issues | Quick health check, issue identification | Replication lag, failures, topology | Interactive SQL queries | Intelligent routing |
| **Analysis** | Aggregation, patterns, query rewrites | Individual queries, locks, waits, real-time metrics | Health snapshot, error patterns, correlations | Lag analysis, failure detection, recommendations | Query execution, result formatting | Multi-agent coordination |
| **Performance Metrics** | Aggregated by query digest | Per-thread metrics (current CPU time, lock wait) | System-wide metrics, lock waits, I/O | Replication lag, binlog position, GTID | Query results | Synthesizes from other agents |
| **Use Case** | Long-term optimization | Real-time troubleshooting | "Something's wrong, where do I start?" | "Is replication healthy?" | "Execute this SQL query" | Unified interface for all tasks |

## How It Works

### Slow Query Agent

1. **Configuration Discovery**: Checks if slow query logging is enabled and where logs are stored
2. **Query Retrieval**: Aggregates slow queries from `mysql.slow_log` table or slow query log file (if `--slow-log-path` provided)
3. **Pattern Analysis**: Identifies top query patterns by total execution time, execution count, and impact
4. **Performance Schema Analysis**: Retrieves aggregated metrics (CPU time, lock wait time, I/O statistics)
5. **Deep Analysis**: Runs `EXPLAIN FORMAT=JSON`, inspects schemas/indexes, analyzes query rewrites
6. **Recommendations**: Provides prioritized suggestions (query rewrites, indexes, configuration)

**File Support**: The agent can read from local slow query log files when `--slow-log-path` is provided, prioritizing the file over `mysql.slow_log` table.

### Running Query Agent

1. **Process List Retrieval**: Queries `information_schema.processlist` to get currently executing queries
2. **Problem Identification**: Identifies long-running queries, blocking queries, and queries in problematic states
3. **Performance Schema Analysis**: Retrieves real-time metrics per thread
4. **Lock Analysis**: Checks for blocking relationships
5. **Deep Query Analysis**: Runs `EXPLAIN FORMAT=JSON`, inspects schemas/indexes
6. **Recommendations**: Provides suggestions for killing queries, query rewrites, resource management

### Incident Triage Agent

1. **Health Snapshot**: Gathers minimal "golden snapshot" of critical health metrics (connections, locks, resources, I/O)
2. **Error Log Analysis**: Reads and extracts patterns from error logs (supports local files and SkySQL API)
3. **SkySQL Observability**: Fetches CPU% and disk utilization metrics from SkySQL Observability API (not accessible via SQL)
4. **Symptom Correlation**: Correlates symptoms into top 2-3 likely causes
5. **Actionable Checklist**: Provides prioritized checklist of immediate checks and safe mitigations
6. **Performance Schema Integration**: Uses `performance_schema` and `information_schema` directly for detailed metrics

**File Support**: The agent prioritizes explicit file paths (`--error-log-path`) over SkySQL API. If a file path is provided, it reads only from that file.

**SkySQL Observability**: For SkySQL services, the agent can fetch CPU% and disk utilization metrics that aren't available via SQL queries. This provides a complete picture of resource pressure.

### Replication Health Agent

1. **Replication Discovery**: Detects master and replica connections in SkySQL/MaxScale environments
2. **Status Collection**: Gathers replication status from all replicas using `SHOW ALL SLAVES STATUS`
3. **Lag Analysis**: Calculates replication lag and identifies lagging replicas
4. **Failure Detection**: Detects replication failures, broken chains, and error conditions
5. **Recommendations**: Provides optimization suggestions for replication topology and configuration

**SkySQL Support**: Works with MaxScale load balancing by executing multiple queries to discover all replicas.

### Database Inspector Agent

1. **Query Execution**: Executes read-only SQL queries (SELECT, SHOW, DESCRIBE, EXPLAIN)
2. **Result Formatting**: Formats query results in clear, readable tables
3. **Context Provision**: Provides insights and interpretation of query results
4. **Safety Guardrails**: Ensures only read-only operations are executed

**Use Cases**: Follow-up analysis after other agents provide recommendations, interactive database exploration, checking configuration and status.

### DBA Orchestrator

1. **Intent Understanding**: Parses user queries to understand what they want
2. **Intelligent Routing**: Routes queries to appropriate specialized agents based on intent
3. **Multi-Agent Coordination**: Coordinates multiple agents for comprehensive analysis when needed
4. **Result Synthesis**: Combines results from multiple agents into coherent, actionable reports
5. **Context Management**: Maintains conversation context across agent interactions
6. **SkySQL Observability**: Can directly access CPU% and disk utilization metrics for SkySQL services
7. **Telemetry Aggregation**: Tracks and reports total LLM usage (tokens, round trips) across all sub-agents invoked

## Performance Schema Integration

Both agents leverage MariaDB's Performance Schema for advanced performance analysis when available. The agents gracefully degrade if Performance Schema is not enabled.

See `enable_performance_schema.sql` for setup instructions.

## Architecture

**Shared Components (`common/`):**
- **`config.py`**: Manages OpenAI API, database, and SkySQL configuration
- **`db_client.py`**: Provides read-only database operations with safety checks, error log reading, SkySQL API integration
- **`guardrails.py`**: Implements input/output guardrails with smart detection for examples vs. real credentials
- **`observability.py`**: Tracks LLM usage metrics (tokens, round trips) with sub-agent aggregation for orchestrator
- **`observability_tools.py`**: SkySQL Observability API integration for CPU% and disk utilization metrics
- **`performance_metrics.py`**: Data structures and helper functions for Performance Schema
- **`performance_tools.py`**: Tools for querying Performance Schema
- **`sys_schema_tools.py`**: Tools for querying performance_schema and information_schema tables directly

**Agent Structure:**
Each agent follows a consistent structure:
- **`agent.py`**: Creates the agent instance with tools, guardrails, and system prompt
- **`tools.py`**: Defines agent-specific tools using `@function_tool` decorator
- **`main.py`**: CLI entry point for one-time analysis
- **`conversation.py`**: Interactive conversation client

## Future Enhancements

See `docs/HIGH_VALUE_AUTOMATION_OPPORTUNITIES.md` for a comprehensive list of planned agents and features.

Upcoming agents:
- **Connection Pool Agent**: Analyze connection usage and leaks
- **Capacity Planning Agent**: Predict resource exhaustion
- **Schema Health Agent**: Identify unused indexes and optimization opportunities
- **Security Audit Agent**: Audit permissions and security
- **Lock & Deadlock Detective Agent**: Detect lock contention and deadlocks

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
- **Orchestrator Telemetry**: Aggregated metrics across all sub-agents (total tokens, round trips, breakdown by agent)

Metrics are automatically logged to `.observability_log.json` and displayed in interactive mode. When using the orchestrator, you'll see both the orchestrator's own usage and the aggregated total across all invoked agents.

## Notes

- All agents only execute read-only SQL queries for safety
- All DDL and configuration changes are presented as suggestions only
- Agents apply guardrails to limit analysis scope
- Input guardrails prevent dangerous SQL injection attempts
- Output guardrails prevent leaking sensitive information
- Agents use async/await patterns as required by the SDK

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Support

- **Issues**: Report bugs or request features on [GitHub Issues](https://github.com/mariadb-JagsR/mariadb-db-agents/issues)
- **Documentation**: See `docs/` directory for detailed documentation
- **Contributing**: See [CONTRIBUTING.md](CONTRIBUTING.md) for contribution guidelines

