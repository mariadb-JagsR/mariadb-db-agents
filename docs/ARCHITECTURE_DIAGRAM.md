# MariaDB Database Management Agents - Architecture Diagram

## Architecture Diagram

![DBA Agent Architecture](DBA_Agent_architecture1.png)

## Highlights

- **Orchestrator** routes queries to all specialized agents and synthesizes results.
- **All agents** apply input/output guardrails for safety.
- **Common infrastructure** provides read-only DB access, observability, and performance tooling.
- **MariaDB Cloud observability** contributes current `/metrics` snapshots, instant
  `/query` results, historical `/query_range` series, and bounded error-log archives.
- **Evidence synthesis** correlates cloud-resource signals with SQL process lists, locks,
  statement digests, slow queries, and replication state.
- **External systems** include MariaDB, the MariaDB Cloud Observability/Provisioning APIs,
  and the OpenAI API.

See [MariaDB Cloud observability and logs](MARIADB_CLOUD_OBSERVABILITY.md) for the API
flow and supported metrics.
