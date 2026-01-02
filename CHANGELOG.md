# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.0] - 2024-12-XX

### Added
- **Slow Query Agent**: Analyzes historical slow queries from slow query logs
  - Pattern detection and aggregation
  - EXPLAIN plan analysis
  - Index recommendations
  - Query rewrite suggestions
  - Fulltext index detection
  - Performance Schema integration
  - Support for reading from local slow query log files (`--slow-log-path`)
  
- **Running Query Agent**: Analyzes currently executing SQL queries in real-time
  - Long-running query detection
  - Blocking query identification
  - Resource-intensive query analysis
  - Performance Schema metrics integration
  
- **Incident Triage Agent**: Quick health check that identifies database issues and provides actionable checklists
  - Health snapshot gathering
  - Error log analysis with pattern extraction
  - Symptom correlation into likely causes
  - Performance Schema and information_schema integration
  - Support for local error log files (`--error-log-path`)
  - SkySQL API integration for error log access
  
- **DBA Orchestrator**: Meta-agent that intelligently routes queries to specialized agents
  - Intelligent routing based on user intent
  - Multi-agent coordination
  - Result synthesis from multiple agents
  - Interactive conversation mode
  - Context management across interactions
  
- **Replication Health Agent**: Monitors replication lag, detects failures, and recommends optimizations
  - Replication lag analysis across all replicas
  - Failure detection and broken chain identification
  - SkySQL/MaxScale support with automatic replica discovery
  - Topology recommendations
  
- **Database Inspector Agent**: Executes read-only SQL queries for follow-up analysis
  - Read-only SQL execution (SELECT, SHOW, DESCRIBE, EXPLAIN)
  - Query result formatting and interpretation
  - Safety guardrails for read-only enforcement
  - Integrated with orchestrator for seamless follow-up
  
- **Unified CLI**: Single command-line interface for all agents
  - `slow-query` command for slow query analysis
  - `running-query` command for running query analysis
  - `incident-triage` command for health checks
  - `orchestrator` command for intelligent routing
  - `replication-health` command for replication monitoring
  - `inspector` command for SQL query execution
  - Interactive conversation mode for all agents
  
- **Common Infrastructure**:
  - Database client with read-only safety checks
  - Performance Schema utilities with MariaDB version compatibility
  - Direct access to performance_schema and information_schema tables (bypassing sys schema)
  - Guardrails for input/output validation
  - Observability tracking for LLM usage
  - Configuration management via environment variables
  - Error log reading with pattern extraction (local files and SkySQL API)
  - Slow query log file reading (local files)
  - SkySQL API integration for error log access
  
- **Documentation**:
  - Comprehensive README with setup and usage instructions
  - Testing guide (TESTING_GUIDE.md)
  - Quick test guide (QUICK_TEST.md)
  - High-value automation opportunities (docs/HIGH_VALUE_AUTOMATION_OPPORTUNITIES.md)
  - Contributing guidelines (CONTRIBUTING.md)
  
- **Project Structure**:
  - Multi-agent architecture for extensibility
  - Modular design with shared common utilities
  - Scripts for generating test slow queries
  - MIT License

### Changed
- Project restructured from single-agent to multi-agent platform
- Removed `service-id` dependency in favor of explicit ENV-based database connections
- Performance Schema queries made compatible with different MariaDB versions

### Security
- All database operations are read-only
- Input guardrails prevent SQL injection
- Output guardrails prevent sensitive data leakage
- `.env` file excluded from version control

### Technical Details
- Built with OpenAI Agents SDK (openai-agents >= 0.6.0)
- Python 3.8+ compatible
- Uses mysql-connector-python for database connectivity
- Async/await patterns throughout

## [Unreleased]

### Added
- **SkySQL Observability Integration**: CPU% and disk utilization metrics via SkySQL Observability API
  - Available in Incident Triage Agent and Orchestrator
  - Automatically fetches deployment region from SkySQL Provisioning API
  - Provides metrics not accessible via SQL (CPU%, disk volume utilization)
  - Integrated into health checks and resource pressure analysis
- **Orchestrator Telemetry Aggregation**: Comprehensive LLM usage tracking across sub-agents
  - Aggregates total tokens and round trips from orchestrator + all sub-agents
  - Provides breakdown by agent for cost analysis
  - Displays both aggregated totals and per-agent breakdown
- **Guardrail Improvements**: Smarter detection of examples vs. real credentials
  - Allows documentation-style examples with placeholders
  - Only triggers on likely real credentials (long alphanumeric strings)
  - More lenient handling of empty outputs when tool calls are present
  - Special handling for orchestrator routing scenarios

### Changed
- Guardrails now distinguish between documentation examples and actual sensitive data
- Orchestrator now tracks and reports aggregated LLM usage from all sub-agents
- SkySQL Observability region detection now uses Provisioning API instead of hostname inference

### Planned
- Connection Pool Agent
- Capacity Planning Agent
- Schema Health Agent
- Security Audit Agent
- Lock & Deadlock Detective Agent
- Comprehensive test suite
- CI/CD pipeline

[0.1.0]: https://github.com/mariadb-JagsR/mariadb-db-agents/releases/tag/v0.1.0


