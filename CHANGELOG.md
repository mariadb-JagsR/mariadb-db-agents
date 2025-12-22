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
  
- **Running Query Agent**: Analyzes currently executing SQL queries in real-time
  - Long-running query detection
  - Blocking query identification
  - Resource-intensive query analysis
  - Performance Schema metrics integration
  
- **Unified CLI**: Single command-line interface for all agents
  - `slow-query` command for slow query analysis
  - `running-query` command for running query analysis
  - Interactive conversation mode for both agents
  
- **Common Infrastructure**:
  - Database client with read-only safety checks
  - Performance Schema utilities with MariaDB version compatibility
  - Guardrails for input/output validation
  - Observability tracking for LLM usage
  - Configuration management via environment variables
  
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

### Planned
- Replication Health Agent
- Connection Pool Agent
- Capacity Planning Agent
- Schema Health Agent
- Security Audit Agent
- DBA Orchestrator Agent
- Comprehensive test suite
- CI/CD pipeline

[0.1.0]: https://github.com/mariadb-JagsR/mariadb-db-agents/releases/tag/v0.1.0

