# MariaDB & MySQL Database Agents

AI-powered DBA assistance for MariaDB and MySQL. Ask questions in plain English — get evidence-backed analysis, root-cause findings, and prioritised action plans. **100% read-only. Nothing is changed without your approval.**

[![Demo](docs/media/dba-assist-demo.gif)](docs/media/dba-assist-demo.gif)

---

## What problems does it solve?

| Situation | Ask the agent |
|-----------|--------------|
| Something is wrong but you don't know where to start | *"Can we get a comprehensive analysis on our DB — performance, everything?"* |
| Queries are slow and you don't know why | *"Analyze slow queries from the last hour"* |
| A runaway query is blocking everyone | *"What queries are running right now?"* |
| You suspect replication is lagging | *"Check replication health"* |
| You need to know whether pressure is persistent or just a spike | *"Show connection and query trends over the last 6 hours"* |
| You want cloud resource context alongside SQL evidence | *"Show MariaDB Cloud CPU and disk now, then correlate with database activity"* |
| You need to investigate something specific | *"Show me the top tables by I/O in the last hour"* |

---

## What does a real response look like?

Here is an actual response to *"Can we get a comprehensive analysis on our DB — performance, everything?"*:

<details>
<summary><strong>Expand full example response</strong></summary>

> **Executive summary** — the DB does not show signs of a broad outage, connection exhaustion, or cache/I/O collapse. Three real issues found:
>
> **1. Row lock contention is the clearest performance problem**
> - Active lock wait observed: 1
> - Average row lock wait time: **4,345 ms**
> - Workload centred on `test_lock_table` with overlapping `SELECT … FOR UPDATE` and `UPDATE … WHERE value BETWEEN …`
>
> **2. A query pattern is causing high temp-table spill to disk**
> - `Created_tmp_disk_tables`: 5,682
> - Disk temp-table ratio: **24.9%**
> - A `GROUP BY / ORDER BY / GROUP_CONCAT(…)` pattern identified as the contributor
>
> **3. Slow-query log is dominated by synthetic workload**
> - Six `SELECT SLEEP(?)` patterns account for ~93% of slow-query time
> - This masks real tuning targets
>
> **Prioritised action plan**
> 1. Fix lock contention — review transactions around the `BETWEEN` range queries on `test_lock_table`
> 2. Tune the temp-table-heavy aggregation query — run `EXPLAIN`, reduce concurrency
> 3. Separate synthetic `SLEEP()` workload from production slow-log analysis
> 4. Re-check replication from a primary-routed admin connection
>
> *Full domain-by-domain breakdown (locking, slow queries, execution plans, connections, I/O, replication, MariaDB Cloud observability) available on request.*

</details>

---

## Quick start (UI)

```bash
git clone https://github.com/mariadb-JagsR/mariadb-db-agents.git
cd mariadb-db-agents

pip install -e .

cp .env.example .env
# Fill in DB_HOST, DB_USER, DB_PASSWORD, OPENAI_API_KEY
# For MariaDB Cloud observability, also set MARIADB_CLOUD_API_KEY

cd mariadb_db_agents
./scripts/run_ui.sh
```

Open **http://127.0.0.1:5173** — a chat interface with config editor, profile switching, agent toggles, and token dashboards.

**Need more queries to try?** See [Sample DBA Questions](docs/SAMPLE_DBA_QUESTIONS.md).

---

## Other ways to use it

**CLI (one-shot)**
```bash
python -m mariadb_db_agents.cli.main orchestrator "Is my database healthy?"
```

**CLI (interactive)**
```bash
python -m mariadb_db_agents.cli.main orchestrator --interactive
```

**IDE via MCP** (Cursor, Windsurf, Claude Code)
```bash
# Add the MCP server to your IDE — see docs/MCP_SETUP.md
# Then ask in chat: "What queries are running right now?"
```

---

## Agents

| Agent | What it analyses |
|-------|-----------------|
| **Orchestrator** | Routes questions, combines SQL/log evidence, and can query current or historical MariaDB Cloud metrics |
| **Slow Query** | Historical slow queries — patterns, EXPLAIN plans, index suggestions |
| **Running Query** | Live processlist — blocking queries, lock waits, current resource usage |
| **Incident Triage** | Broad health snapshot — connections, locks, I/O, error logs, current cloud resources, and supported metric trends |
| **Replication Health** | Replica lag, broken chains, GTID state |
| **Database Inspector** | Ad-hoc read-only SQL with AI interpretation of results |

All agents are **read-only**. Recommendations are suggestions only — nothing is applied automatically.

---

## Setup & configuration

### Environment variables (`.env`)

| Variable | Required | Description |
|----------|----------|-------------|
| `OPENAI_API_KEY` | Yes | OpenAI API key |
| `OPENAI_MODEL` | No | OpenAI model to use (code default: `gpt-5.2`) |
| `DB_HOST` | Yes | MariaDB/MySQL host |
| `DB_PORT` | No | Port (default: 3306) |
| `DB_USER` | Yes | Read-only database user |
| `DB_PASSWORD` | Yes | Database password |
| `DB_DATABASE` | Yes | Default database |
| `MARIADB_CLOUD_API_KEY` | No | MariaDB Cloud API key — enables error logs and CPU/disk metrics |
| `MARIADB_CLOUD_SERVICE_ID` | No | MariaDB Cloud service ID |
| `MARIADB_CLOUD_LOG_API_URL` | No | MariaDB Cloud Log API URL |

### Recommended DB user

```sql
CREATE USER 'dba_readonly'@'%' IDENTIFIED BY 'strongpassword';
GRANT SELECT, PROCESS, REPLICATION CLIENT ON *.* TO 'dba_readonly'@'%';
```

---

## Architecture

![Architecture](docs/DBA_Agent_architecture1.png)

- **Orchestrator** routes to specialised agents and synthesises multi-agent results
- **Common infrastructure** (`common/`) provides read-only DB access, guardrails, observability tracking, and MariaDB Cloud API integration
- **Each agent** follows the same structure: `agent.py` (prompt + tools), `tools.py` (@function_tool definitions), `main.py` (CLI entry), `conversation.py` (interactive mode)

See [Architecture details](docs/ARCHITECTURE_DIAGRAM.md) for more.

---

## MariaDB Cloud observability

The platform can enrich SQL analysis with MariaDB Cloud control-plane evidence that is not
available from the database connection itself:

- **Current snapshot** — CPU, data/log disk utilisation, service availability, connected and
  running threads, and aborted clients/connections.
- **Historical trends** — PromQL range queries for supported time-series metrics such as
  connected/running threads, query counters, slow-query counters, table-lock waits,
  replication lag, and service availability.
- **Custom PromQL** — the orchestrator can issue instant or range queries when a curated
  metric is not enough.
- **Error logs** — API-based archive discovery, bounded download, pattern grouping,
  severity classification, and first/last-seen timestamps.
- **Automatic targeting** — resolves the service name and observability region from the
  MariaDB Cloud service metadata and database hostname.

This lets the agent answer questions such as:

> “Was connection pressure sustained during the last six hours, or is the current value
> just a spike?”

> “Show CPU and disk now, then compare query, slow-query, and replication-lag trends over
> the last 24 hours.”

Configure `MARIADB_CLOUD_API_KEY`, `MARIADB_CLOUD_SERVICE_ID`, and optionally
`MARIADB_CLOUD_LOG_API_URL` in `.env`. The current API and database hostnames retain the
`skysql.com` domain.

Important: `/metrics` provides the current CPU and disk snapshot. Historical
`/query_range` data is available only for series retained by the metrics backend; the agent
reports unavailable series rather than inventing a trend.

See [MariaDB Cloud observability and logs](docs/MARIADB_CLOUD_OBSERVABILITY.md) for
supported metrics, examples, API behavior, and test commands.

---

## Roadmap

Planned agents: Connection Pool Analyser · Capacity Planning · Schema & Index Health · Lock & Deadlock Detective · Security Audit

See [HIGH_VALUE_AUTOMATION_OPPORTUNITIES.md](docs/HIGH_VALUE_AUTOMATION_OPPORTUNITIES.md) for the full list.

---

## Tech stack

| Layer | Technology |
|-------|-----------|
| **LLM framework** | [OpenAI Agents SDK](https://github.com/openai/openai-agents-python) (`openai-agents ≥ 0.6`) |
| **LLM model** | Configurable OpenAI model via `OPENAI_MODEL` |
| **Backend API** | [FastAPI](https://fastapi.tiangolo.com/) + [Uvicorn](https://www.uvicorn.org/) |
| **Frontend** | [React 18](https://react.dev/) + [Vite 5](https://vitejs.dev/) |
| **Markdown rendering** | [react-markdown](https://github.com/remarkjs/react-markdown) + remark-gfm |
| **Database client** | [mysql-connector-python 9](https://dev.mysql.com/doc/connector-python/en/) |
| **Config / secrets** | [python-dotenv](https://github.com/theskumar/python-dotenv) + Pydantic |
| **IDE integration** | [MCP SDK](https://github.com/modelcontextprotocol/python-sdk) (Cursor, Windsurf, Claude Code) |
| **UI theme** | MariaDB Cloud design language — dark teal-navy nav, blue accents, light card body |

Full stack details and architectural notes: [docs/TECH_STACK.md](docs/TECH_STACK.md).

---

## License

MIT — see [LICENSE](LICENSE).
