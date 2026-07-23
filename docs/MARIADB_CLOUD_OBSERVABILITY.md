# MariaDB Cloud Observability and Logs

MariaDB Cloud adds a control-plane view to the agents' read-only SQL evidence. The
integration can answer both **what is happening now** and, for retained time-series
metrics, **how the signal changed over a requested period**.

## Why this matters

A live process list can explain current blockers, but it cannot tell you whether a
connection spike lasted two minutes or six hours. SQL also cannot expose managed-service
CPU and volume utilisation. MariaDB Cloud observability fills those gaps:

1. Fetch a current cloud resource snapshot.
2. Query retained metric history with PromQL.
3. Retrieve error-log archives for a bounded period.
4. Correlate those signals with process lists, locks, statement digests, replication, and
   slow-query evidence.

All access is read-only.

## API capabilities

The integration uses the following MariaDB Cloud endpoints:

| Endpoint | Purpose | Response |
|----------|---------|----------|
| `GET /observability/v2/metrics` | Current metrics scrape | Prometheus text |
| `GET /observability/v2/query` | Instant PromQL query | Prometheus JSON vector |
| `GET /observability/v2/query_range` | Historical PromQL query | Prometheus JSON matrix |
| `GET /observability/v2/logs` | Discover logs in a time range | JSON metadata |
| `GET /observability/v2/logs/archive` | Download selected logs | Archive |
| `GET /provisioning/v1/services/{id}` | Resolve service name and region | JSON metadata |

The API hostname remains `api.skysql.com`.

## Agent tools

### Current snapshot and curated history

`get_mariadb_cloud_observability_snapshot`

- With no `hours`, returns the current snapshot.
- With `hours=N`, also requests historical summaries for selected catalog metrics.
- Accepts `metric_names` to limit historical queries.
- Selects a safe default step based on the requested window.
- Caps history requests at seven days.

Example agent request:

> Show MariaDB Cloud CPU and disk now, plus connected threads, running threads, slow
> queries, and replication lag over the last six hours.

Conceptual tool call:

```text
get_mariadb_cloud_observability_snapshot(
  hours=6,
  metric_names=[
    "threads_connected",
    "threads_running",
    "slow_queries",
    "replication_lag_seconds"
  ]
)
```

### Custom PromQL

`query_mariadb_cloud_observability_metrics`

- Omitting `hours` runs an instant query.
- Setting `hours` runs a range query.
- Returns bounded summaries instead of dumping an unbounded time series into the model.

Example:

```text
query_mariadb_cloud_observability_metrics(
  query='max(mariadb_global_status_threads_running{mariadb="my-service"})',
  hours=24,
  step_seconds=900
)
```

Custom PromQL is available to the orchestrator. Incident triage uses the curated snapshot
and history tool.

## Curated metrics

| Metric key | Signal | Current snapshot | Historical range |
|------------|--------|------------------|------------------|
| `cpu` | Managed-service CPU utilisation | Yes | Backend-dependent; currently treated as snapshot-only |
| `disk_data_utilization` | Data-volume utilisation | Yes | Snapshot-only |
| `disk_logs_utilization` | Log-volume utilisation | Yes | Snapshot-only |
| `threads_connected` | Open database connections | Yes | Yes |
| `threads_running` | Active database threads | Yes | Yes |
| `slow_queries` | Cumulative slow-query counter | Not in curated snapshot | Yes |
| `queries` | Cumulative query counter | Not in curated snapshot | Yes |
| `table_locks_waited` | Cumulative table-lock waits | Not in curated snapshot | Yes |
| `replication_lag_seconds` | Seconds behind primary | Not in curated snapshot | Yes |
| `mariadb_up` | Service availability | Yes | Yes |

Counters are not rates. The returned history includes first, last, minimum, maximum,
average, and delta so the agent can distinguish a large old counter from growth during the
requested window.

## Configuration

```bash
MARIADB_CLOUD_API_KEY=skysql....
MARIADB_CLOUD_SERVICE_ID=dbpgp12345678
MARIADB_CLOUD_LOG_API_URL=https://api.skysql.com/observability/v2/logs
```

`MARIADB_CLOUD_API_KEY` is required for cloud API access.

`MARIADB_CLOUD_SERVICE_ID` is recommended. For metrics, the implementation can infer the
namespace from `DB_HOST`; it then uses the Provisioning API to resolve the human service
name and deployment region.

## Service and region resolution

The metrics APIs use two related identifiers:

- **Namespace/service ID**, such as `dbpgp12345678`
- **Provisioning service name**, such as `production-orders`

The `/metrics` endpoint's `service` query parameter expects the service name, while metric
labels and database hostnames often carry the service ID. The integration resolves both
before querying, avoiding empty results caused by sending the ID where the name is
required.

Deployment regions are mapped to these observability regions:

- `us-central1`
- `europe-west1`
- `asia-southeast1`

## CLI and integration tests

Current snapshot:

```bash
python scripts/mariadb_cloud_observability_snapshot.py
```

Snapshot plus six hours of selected history:

```bash
python scripts/test_observability_snapshot.py \
  --hours 6 \
  --metrics threads_connected threads_running slow_queries replication_lag_seconds
```

Custom PromQL range:

```bash
python scripts/test_observability_snapshot.py \
  --query 'max(mariadb_global_status_threads_running{mariadb="my-service"})' \
  --hours 6 \
  --step-seconds 300
```

Error-log API:

```bash
python scripts/test_mariadb_cloud_error_logs.py --test-api-only
```

See [the error-log integration guide](../scripts/TEST_MARIADB_CLOUD_LOGS.md) for archive
download and extraction examples.

## Direct API examples

Current metrics:

```bash
curl -G 'https://api.skysql.com/observability/v2/metrics' \
  --data-urlencode 'service=my-service' \
  -H 'X-Observability-Region: us-central1' \
  -H 'X-API-Key: YOUR_MARIADB_CLOUD_API_KEY'
```

Historical range:

```bash
curl -G 'https://api.skysql.com/observability/v2/query_range' \
  --data-urlencode 'query=max(mariadb_global_status_threads_running{mariadb="my-service"})' \
  --data-urlencode 'start=1784750400' \
  --data-urlencode 'end=1784772000' \
  --data-urlencode 'step=300' \
  -H 'X-Observability-Region: us-central1' \
  -H 'X-API-Key: YOUR_MARIADB_CLOUD_API_KEY'
```

## Evidence and failure behavior

The integration is intentionally explicit:

- Empty history is reported as unavailable, not interpreted as zero.
- Missing CPU or volume series does not become a database incident.
- API authentication, network, and service-resolution failures return structured
  unavailable results.
- Historical summaries include the actual point count and observed time boundaries.
- Log processing limits archive size, lines, and extracted patterns before model analysis.

This keeps recommendations grounded in data returned during the current agent run.

## Known limits

- CPU and volume utilisation are currently reliable as current `/metrics` snapshots; they
  may not exist in the historical metrics store.
- Metric availability varies by topology and exporter version.
- A cumulative counter needs delta/rate interpretation; its absolute value alone is not a
  recent incident signal.
- The default historical window is bounded to avoid large Prometheus responses and
  excessive model context.
