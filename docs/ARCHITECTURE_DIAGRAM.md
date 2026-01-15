# MariaDB Database Management Agents - Architecture Diagram

## Architecture Diagram

![DBA Agent Architecture](DBA_Agent_architecture1.png)

## Highlights

- **Orchestrator** routes queries to all specialized agents and synthesizes results.
- **All agents** apply input/output guardrails for safety.
- **Common infrastructure** provides read-only DB access, observability, and performance tooling.
- **External systems** include MariaDB, SkySQL Observability API, and OpenAI API.
