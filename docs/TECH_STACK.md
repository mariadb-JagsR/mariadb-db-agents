# Tech Stack

Full breakdown of every technology used in the MariaDB Database Agents platform, grouped by layer.

---

## AI / LLM

| Component | Choice | Why |
|-----------|--------|-----|
| **LLM framework** | [OpenAI Agents SDK](https://github.com/openai/openai-agents-python) (`openai-agents ≥ 0.6`) | Native agentic loop, `@function_tool` decorator, built-in handoffs between agents, streaming support, and per-request token accounting. |
| **LLM model** | Configurable via `OPENAI_MODEL` (code default: `gpt-5.2`) | Lets deployments choose the reasoning/cost profile appropriate for DBA investigations. |
| **Guardrails** | Custom (`common/guardrails.py`) | Input sanitisation + output validation layer wrapping each agent. Prevents prompt injection and sensitive data leakage. |
| **Observability** | Custom token tracker (`common/observability.py`) | Captures input/output/cached/reasoning tokens per LLM request, aggregates across orchestrator + sub-agents, persists to `.observability_log.json`. |

---

## Backend

| Component | Choice | Notes |
|-----------|--------|-------|
| **API framework** | [FastAPI](https://fastapi.tiangolo.com/) 0.116+ | Async REST API. Pydantic models for request/response validation. |
| **ASGI server** | [Uvicorn](https://www.uvicorn.org/) 0.35+ | Runs the FastAPI app. |
| **Streaming** | Server-Sent Events (SSE) over HTTP | `ui_api/streaming.py` — emits `token`, `tool_call`, `tool_result`, `handoff`, `evidence`, `usage`, `done`, `error` events. |
| **Config management** | [python-dotenv](https://github.com/theskumar/python-dotenv) 1.0+ | Loads `.env`; `config_service.py` handles atomic writes with `.env.bak` backup. |
| **Data validation** | [Pydantic](https://docs.pydantic.dev/) v2 (via FastAPI) | Request/response schemas in `ui_api/schemas.py`. |
| **Persistence** | JSON files in `.ui_data/` | Sessions, profiles, agent toggles, run history. No database required for the tool itself. |
| **DB client** | [mysql-connector-python](https://dev.mysql.com/doc/connector-python/en/) 9.0+ | Connects to MariaDB / MySQL. SSL support for MariaDB Cloud. Session-level `READ ONLY` transaction mode enforced on every connection. |
| **MariaDB Cloud API** | REST + PromQL (`common/observability_tools.py`, `common/db_client.py`) | Fetches current Prometheus metrics, instant/range history, service metadata, and bounded error-log archives when `MARIADB_CLOUD_API_KEY` is set. |
| **IDE integration** | [MCP SDK](https://github.com/modelcontextprotocol/python-sdk) 0.9+ | Exposes agents as MCP tools for Cursor, Windsurf, and Claude Code. See `mcp_server/`. |

---

## Frontend

| Component | Choice | Notes |
|-----------|--------|-------|
| **UI framework** | [React 18.3](https://react.dev/) | Function components + hooks. No external state-management library. |
| **Build tool** | [Vite 5.4](https://vitejs.dev/) | Fast dev server (HMR), production bundling. |
| **Markdown rendering** | [react-markdown 9](https://github.com/remarkjs/react-markdown) + [remark-gfm 4](https://github.com/remarkjs/remark-gfm) | Renders assistant responses. Raw text is shown during streaming to avoid re-parsing partial Markdown on every token flush (flicker prevention). |
| **Streaming** | Native `fetch` with SSE parsing (`ui_web/src/api.js`) | Tokens are coalesced in a 60 ms flush timer before updating React state to reduce render frequency. |
| **Fonts** | DM Sans (display/body) · JetBrains Mono (code) | Loaded from Google Fonts. |
| **Theme** | MariaDB Cloud design language | Dark teal-navy top bar (`#0d2233`), white sidebar and cards, light blue-gray body (`#f0f4f8`), blue interactive accent (`#0066cc`). CSS custom properties throughout — no CSS-in-JS. |
| **Browser testing** | [Playwright 1.49](https://playwright.dev/) | Used for demo GIF capture (`ui_web/scripts/capture-readme-demo.mjs`). |

---

## Agents

The platform uses six agents, each in its own directory under `agents/` (except the orchestrator):

| Agent | Directory | Role |
|-------|-----------|------|
| **Orchestrator** | `orchestrator/` | Routes user questions to the right specialist(s); synthesises multi-agent results |
| **Slow Query** | `agents/slow_query/` | Analyses the slow-query log — patterns, EXPLAIN plans, index suggestions |
| **Running Query** | `agents/running_query/` | Live processlist — blocking queries, lock waits, resource usage |
| **Incident Triage** | `agents/incident_triage/` | Broad health snapshot — connections, locks, I/O, error logs, current cloud resources, and curated metric history |
| **Replication Health** | `agents/replication_health/` | Replica lag, broken chains, GTID state |
| **Database Inspector** | `agents/database_inspector/` | Ad-hoc read-only SQL with AI interpretation of results |

Each agent follows the same structure:

```
agents/<name>/
  agent.py          # System prompt + agent creation
  tools.py          # @function_tool definitions
  main.py           # CLI entry point
  conversation.py   # Interactive mode
```

---

## Common infrastructure (`common/`)

| Module | Purpose |
|--------|---------|
| `config.py` | Loads and validates env vars for OpenAI, database, and MariaDB Cloud |
| `db_client.py` | Read-only SQL execution — `is_read_only_sql()` blocklist, schema auto-resolution, slow-log and error-log helpers, MariaDB Cloud log API |
| `guardrails.py` | Input/output validation on every agent |
| `observability.py` | Per-request token tracking, aggregation, persistence |
| `observability_tools.py` | MariaDB Cloud `/metrics`, `/query`, and `/query_range` client; service/region resolution; bounded time-series summaries |
| `performance_tools.py` | Performance Schema query helpers |
| `sys_schema_tools.py` | `sys` schema query helpers |

---

## Python dependencies (key packages)

```
openai-agents >= 0.6.0       # Agentic loop, tool routing, streaming
fastapi >= 0.116.0            # REST API
uvicorn >= 0.35.0             # ASGI server
mysql-connector-python >= 9.0 # MariaDB / MySQL client
python-dotenv >= 1.0          # .env loading
pydantic >= 2.0               # Data validation
mcp >= 0.9.0                  # MCP server for IDE integration
```

Full pinned list: [`requirements.txt`](../requirements.txt).

---

## Frontend dependencies (key packages)

```
react ^18.3.1
react-dom ^18.3.1
vite ^5.4.21
react-markdown ^9.0.1
remark-gfm ^4.0.0
```

Full list: [`ui_web/package.json`](../ui_web/package.json).

---

## Data flow

```
User (browser / CLI / IDE)
        │
        ▼
FastAPI  /chat/orchestrator/run   (SSE stream)
        │
        ▼
orchestrator_service.py
  • Builds conversation context (last 12 messages + summarised older)
  • Calls OpenAI Agents SDK
        │
        ▼
Orchestrator Agent
  • Parses intent → routes to 1–N specialist agents
        │
        ▼
Specialist Agents  (each tool-calls into →)
  • common/db_client.py     (guardrailed SQL + cloud error-log archives)
  • common/observability_tools.py  (current + historical MariaDB Cloud metrics)
        │
        ▼
Results synthesised → SSE events → React UI
```

For the metrics/log data flow, supported catalog, and direct API examples, see
[`MARIADB_CLOUD_OBSERVABILITY.md`](MARIADB_CLOUD_OBSERVABILITY.md).

---

## Security design

- **Read-only enforcement**: `is_read_only_sql()` blocks all write/DDL/DCL SQL keywords; connections additionally run under `SET SESSION TRANSACTION READ ONLY`.
- **Schema resolution**: corrects common LLM schema mistakes (e.g. `mysql.my_table`) by querying `information_schema.TABLES`.
- **Secret masking**: API responses always redact `OPENAI_API_KEY`, `DB_PASSWORD`, and `MARIADB_CLOUD_API_KEY` with `********`.
- **Input/output guardrails**: applied at the orchestrator layer; rejects injected SQL and strips data that shouldn't leave the assistant response.
- **No credentials in code**: all secrets via environment variables only.
