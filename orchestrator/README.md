# DBA Orchestrator Agent

The DBA Orchestrator Agent is a meta-agent that acts as the primary entry point for database management tasks. It intelligently routes user queries to specialized agents, coordinates multi-agent analysis, and synthesizes comprehensive reports.

## Overview

Instead of knowing which specific agent to use, you can ask the orchestrator natural language questions, and it will:
1. Understand your intent
2. Route to appropriate specialized agents
3. Coordinate multiple agents when needed
4. Synthesize results into a comprehensive report

## Usage

### Via Unified CLI

```bash
# Simple query
python -m mariadb_db_agents.cli.main orchestrator "Is my database healthy?"

# Analyze slow queries
python -m mariadb_db_agents.cli.main orchestrator "Analyze slow queries from the last hour"

# Comprehensive health check
python -m mariadb_db_agents.cli.main orchestrator "Do a full health check"

# Interactive mode (prompts for query)
python -m mariadb_db_agents.cli.main orchestrator
```

### Direct Invocation

```bash
python -m mariadb_db_agents.orchestrator.main "What queries are running right now?"
```

## Examples

### Example 1: Health Check

```bash
python -m mariadb_db_agents.cli.main orchestrator "Is my database healthy?"
```

**What happens:**
- Orchestrator routes to Incident Triage Agent (quick health check)
- May also route to Running Query Agent for current state
- May route to Replication Health Agent if replication issues detected
- Synthesizes results into comprehensive health report

### Example 2: Performance Investigation

```bash
python -m mariadb_db_agents.cli.main orchestrator "Why are queries slow?"
```

**What happens:**
- Orchestrator routes to Incident Triage Agent first
- Based on findings, routes to Slow Query Agent or Running Query Agent
- Synthesizes findings to identify root cause

### Example 3: Specific Analysis

```bash
python -m mariadb_db_agents.cli.main orchestrator "Analyze slow queries from the last 3 hours, focus on top 5 patterns"
```

**What happens:**
- Orchestrator routes directly to Slow Query Agent
- Extracts parameters: hours=3.0, max_patterns=5
- Returns Slow Query Agent's analysis

## Available Agents

The orchestrator can route to:

1. **Slow Query Agent** - Historical slow query analysis
2. **Running Query Agent** - Real-time query analysis
3. **Incident Triage Agent** - Quick health checks and issue identification
4. **Replication Health Agent** - Monitor replication lag and health
5. **Database Inspector Agent** - Execute read-only SQL queries for investigation

More agents will be added as they are implemented.

## Routing Logic

The orchestrator uses LLM-based intent classification to route queries:

- **"slow queries"** / **"query performance"** → Slow Query Agent
- **"running queries"** / **"current queries"** → Running Query Agent
- **"replication"** / **"replica lag"** / **"replication health"** → Replication Health Agent
- **"execute SQL"** / **"query database"** / **"check information_schema"** → Database Inspector Agent
- **"health check"** / **"something's wrong"** → Incident Triage Agent
- **"is my database healthy?"** → Incident Triage + Running Query
- **"why is it slow?"** → Incident Triage → (Slow Query or Running Query based on findings)

## Multi-Agent Coordination

For complex queries, the orchestrator can coordinate multiple agents:

1. **Start with Incident Triage** for quick overview
2. **Route to specific agents** based on findings
3. **Synthesize results** from all agents into unified report

Example: "Is my database healthy?"
- Runs Incident Triage (quick check)
- Runs Running Query (current state)
- Synthesizes: "Database is healthy. 5 active queries, all normal."

## Output Format

The orchestrator provides structured reports:

**Executive Summary**
[Overview of analysis and key findings]

**Analysis Results**
[Findings from each agent used]

**Correlated Findings**
[How findings relate to each other]

**Recommendations** (Prioritized)
[Actionable next steps]

**Next Steps**
[Follow-up suggestions]

## Configuration

Database connection is configured via environment variables:
- `DB_HOST`
- `DB_PORT`
- `DB_USER`
- `DB_PASSWORD`
- `DB_DATABASE`

OpenAI API key is configured via:
- `OPENAI_API_KEY`

For SkySQL error log access:
- `SKYSQL_API_KEY`
- `SKYSQL_SERVICE_ID`

## Architecture

The orchestrator uses a tool-based approach:
- Each specialized agent is wrapped as a tool
- Orchestrator LLM selects which tools to call
- Results are synthesized into comprehensive reports

See `ORCHESTRATOR_PLAN.md` for detailed architecture and `ADVANCED_WORKFLOWS.md` for future enhancements.

## Future Enhancements

- Parallel agent execution
- Result caching
- Advanced conditional workflows
- Proactive monitoring
- Scheduled health checks

See `ADVANCED_WORKFLOWS.md` for details on advanced multi-agent workflows.

