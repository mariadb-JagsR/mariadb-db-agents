# common/observability_tools.py
"""
MariaDB Cloud observability tools for fetching CPU, disk, and system metrics.

Supports:
- GET /observability/v2/metrics — current Prometheus text snapshot
- GET /observability/v2/query — instant PromQL
- GET /observability/v2/query_range — historical PromQL time series
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any, Dict, Iterable, List, Optional, Tuple

import requests
from agents import function_tool

from .config import DBConfig, MariaDBCloudConfig

logger = logging.getLogger(__name__)

OBSERVABILITY_BASE_URL = "https://api.skysql.com/observability/v2"
METRICS_URL = f"{OBSERVABILITY_BASE_URL}/metrics"
QUERY_URL = f"{OBSERVABILITY_BASE_URL}/query"
QUERY_RANGE_URL = f"{OBSERVABILITY_BASE_URL}/query_range"
PROVISIONING_SERVICE_URL = "https://api.skysql.com/provisioning/v1/services"

VALID_OBSERVABILITY_REGIONS = frozenset({"us-central1", "europe-west1", "asia-southeast1"})

DEFAULT_HISTORY_HOURS = 1
DEFAULT_STEP_SECONDS = 300
MAX_HISTORY_HOURS = 168
MAX_HISTORY_POINTS = 500

# Metrics available on the /metrics snapshot (namespace/server_name/service_name labels).
SNAPSHOT_METRIC_NAMES = frozenset(
    {
        "mariadb_server_cpu",
        "mariadb_server_volume_stats_used_bytes",
        "mariadb_server_volume_stats_capacity_bytes",
        "mariadb_up",
        "mariadb_global_status_threads_connected",
        "mariadb_global_status_threads_running",
        "mariadb_global_status_aborted_clients",
        "mariadb_global_status_aborted_connects",
    }
)

# Curated metrics for agents. History uses PromQL with mariadb="{service_name}" labels.
METRIC_CATALOG: dict[str, dict[str, Any]] = {
    "cpu": {
        "label": "CPU utilization",
        "snapshot_metric": "mariadb_server_cpu",
        "history_promql": None,
        "unit": "percent",
    },
    "disk_data_utilization": {
        "label": "Data disk utilization",
        "snapshot_only": True,
        "disk_purpose": "data",
        "unit": "percent",
    },
    "disk_logs_utilization": {
        "label": "Logs disk utilization",
        "snapshot_only": True,
        "disk_purpose": "logs",
        "unit": "percent",
    },
    "threads_connected": {
        "label": "Threads connected",
        "history_promql": 'max(mariadb_global_status_threads_connected{{mariadb="{service_name}"}})',
        "unit": "count",
    },
    "threads_running": {
        "label": "Threads running",
        "history_promql": 'max(mariadb_global_status_threads_running{{mariadb="{service_name}"}})',
        "unit": "count",
    },
    "slow_queries": {
        "label": "Slow queries (counter)",
        "history_promql": 'max(mariadb_global_status_slow_queries{{mariadb="{service_name}"}})',
        "unit": "count",
    },
    "queries": {
        "label": "Total queries (counter)",
        "history_promql": 'max(mariadb_global_status_queries{{mariadb="{service_name}"}})',
        "unit": "count",
    },
    "table_locks_waited": {
        "label": "Table locks waited (counter)",
        "history_promql": 'max(mariadb_global_status_table_locks_waited{{mariadb="{service_name}"}})',
        "unit": "count",
    },
    "replication_lag_seconds": {
        "label": "Replication lag (seconds behind master)",
        "history_promql": 'max(mariadb_slave_status_seconds_behind_master{{mariadb="{service_name}"}})',
        "unit": "seconds",
    },
    "mariadb_up": {
        "label": "MariaDB up",
        "history_promql": 'max(mariadb_up{{mariadb="{service_name}"}})',
        "unit": "boolean",
    },
}


@dataclass(frozen=True)
class Sample:
    """A single metric sample from Prometheus text format."""

    name: str
    labels: Dict[str, str]
    value: float
    ts_ms: Optional[int] = None


@dataclass(frozen=True)
class ObservabilityContext:
    namespace: str
    service_name: str
    region: str
    deployment_region: str | None = None


METRIC_LINE_RE = re.compile(
    r"""
    ^
    (?P<name>[a-zA-Z_:][a-zA-Z0-9_:]*)       # metric name
    (?:\{(?P<labels>[^}]*)\})?              # optional {labels}
    \s+
    (?P<value>[-+]?(?:\d+\.?\d*|\d*\.?\d+)(?:[eE][-+]?\d+)?)  # value
    (?:\s+(?P<ts>\d+))?                     # optional timestamp (ms in MariaDB Cloud output)
    \s*$
    """,
    re.VERBOSE,
)

LABEL_RE = re.compile(r'(\w+)\s*=\s*"((?:\\.|[^"\\])*)"')


def parse_labels(label_blob: str) -> Dict[str, str]:
    """Parse Prometheus label string into dictionary."""
    labels: Dict[str, str] = {}
    if not label_blob:
        return labels
    for match in LABEL_RE.finditer(label_blob):
        key = match.group(1)
        value = match.group(2)
        value = value.replace(r"\\", "\\").replace(r"\"", '"')
        labels[key] = value
    return labels


def parse_prometheus_text(text: str) -> List[Sample]:
    """Parse Prometheus text exposition format into Sample objects."""
    samples: List[Sample] = []
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        match = METRIC_LINE_RE.match(line)
        if not match:
            continue
        labels = parse_labels(match.group("labels") or "")
        try:
            value = float(match.group("value"))
        except ValueError:
            continue
        ts_str = match.group("ts")
        ts_ms = int(ts_str) if ts_str else None
        samples.append(
            Sample(
                name=match.group("name"),
                labels=labels,
                value=value,
                ts_ms=ts_ms,
            )
        )
    return samples


def _observability_headers(api_key: str, region: str, accept: str = "text/plain") -> dict[str, str]:
    return {
        "X-API-Key": api_key,
        "X-Observability-Region": region,
        "accept": accept,
    }


def fetch_metrics(
    api_key: str,
    region: str,
    *,
    service_name: str | None = None,
    timeout_s: int = 30,
) -> str:
    """Fetch current metrics from MariaDB Cloud /observability/v2/metrics."""
    params: dict[str, str] = {}
    if service_name:
        params["service"] = service_name
    response = requests.get(
        METRICS_URL,
        headers=_observability_headers(api_key, region),
        params=params or None,
        timeout=timeout_s,
    )
    response.raise_for_status()
    return response.text


def query_prometheus_instant(
    api_key: str,
    region: str,
    query: str,
    *,
    eval_time: datetime | None = None,
    timeout_s: int = 30,
) -> dict[str, Any]:
    """Run an instant PromQL query against /observability/v2/query."""
    params: dict[str, str | int] = {"query": query}
    if eval_time is not None:
        params["time"] = int(eval_time.timestamp())
    response = requests.get(
        QUERY_URL,
        headers=_observability_headers(api_key, region, accept="application/json"),
        params=params,
        timeout=timeout_s,
    )
    response.raise_for_status()
    return response.json()


def query_prometheus_range(
    api_key: str,
    region: str,
    query: str,
    *,
    start: datetime,
    end: datetime,
    step_seconds: int = DEFAULT_STEP_SECONDS,
    timeout_s: int = 60,
) -> dict[str, Any]:
    """Run a range PromQL query against /observability/v2/query_range."""
    params = {
        "query": query,
        "start": int(start.timestamp()),
        "end": int(end.timestamp()),
        "step": max(1, step_seconds),
    }
    response = requests.get(
        QUERY_RANGE_URL,
        headers=_observability_headers(api_key, region, accept="application/json"),
        params=params,
        timeout=timeout_s,
    )
    response.raise_for_status()
    return response.json()


def filter_samples(
    samples: Iterable[Sample],
    namespace: str,
    service_name: Optional[str] = None,
    server_name: Optional[str] = None,
) -> List[Sample]:
    """Filter samples by namespace, service_name, and server_name."""
    filtered: List[Sample] = []
    for sample in samples:
        if sample.labels.get("namespace") != namespace:
            continue
        if service_name and sample.labels.get("service_name") != service_name:
            continue
        if server_name and sample.labels.get("server_name") != server_name:
            continue
        filtered.append(sample)
    return filtered


def latest_by_series(
    samples: Iterable[Sample],
) -> Dict[Tuple[str, Tuple[Tuple[str, str], ...]], Sample]:
    """Keep the latest sample per metric + label set."""
    best: Dict[Tuple[str, Tuple[Tuple[str, str], ...]], Sample] = {}
    for sample in samples:
        key = (sample.name, tuple(sorted(sample.labels.items())))
        previous = best.get(key)
        if not previous:
            best[key] = sample
            continue
        if sample.ts_ms is not None and (previous.ts_ms is None or sample.ts_ms >= previous.ts_ms):
            best[key] = sample
        elif sample.ts_ms is None:
            best[key] = sample
    return best


def disk_utilization(samples: Iterable[Sample]) -> List[Dict[str, object]]:
    """Extract disk utilization from volume stats metrics."""
    used: dict[tuple[str | None, str | None], float] = {}
    capacity: dict[tuple[str | None, str | None], float] = {}

    for sample in samples:
        key = (sample.labels.get("server_name"), sample.labels.get("disk_purpose"))
        if sample.name == "mariadb_server_volume_stats_used_bytes":
            used[key] = sample.value
        elif sample.name == "mariadb_server_volume_stats_capacity_bytes":
            capacity[key] = sample.value

    rows: List[Dict[str, object]] = []
    for key, used_bytes in used.items():
        cap_bytes = capacity.get(key)
        if not cap_bytes or cap_bytes <= 0:
            continue
        server, purpose = key
        pct = (used_bytes / cap_bytes) * 100.0
        rows.append(
            {
                "server_name": server,
                "disk_purpose": purpose,
                "used_bytes": used_bytes,
                "capacity_bytes": cap_bytes,
                "utilization_pct": pct,
                "remaining_bytes": max(cap_bytes - used_bytes, 0.0),
            }
        )
    rows.sort(key=lambda row: float(row["utilization_pct"]), reverse=True)
    return rows


def get_single_value(
    samples: Iterable[Sample],
    metric: str,
    label_filter: Dict[str, str] | None = None,
) -> Optional[float]:
    """Return the max value among matching samples."""
    values: List[float] = []
    for sample in samples:
        if sample.name != metric:
            continue
        if label_filter:
            if any(sample.labels.get(key) != value for key, value in label_filter.items()):
                continue
        values.append(sample.value)
    return max(values) if values else None


def build_health_snapshot(samples: List[Sample]) -> Dict[str, object]:
    """Build a current health snapshot from metric samples."""
    snapshot: Dict[str, object] = {"disk": disk_utilization(samples)}

    cpu = get_single_value(samples, "mariadb_server_cpu")
    if cpu is not None:
        cpu_pct = cpu * 100.0 if cpu <= 1.5 else cpu
        snapshot["cpu"] = {"raw": cpu, "cpu_pct_est": cpu_pct}
    else:
        snapshot["cpu"] = {
            "note": "mariadb_server_cpu not present in /metrics for this namespace (skipping)"
        }

    snapshot["mariadb_up_max"] = get_single_value(samples, "mariadb_up")
    snapshot["threads_connected_max"] = get_single_value(
        samples, "mariadb_global_status_threads_connected"
    )
    snapshot["threads_running_max"] = get_single_value(
        samples, "mariadb_global_status_threads_running"
    )
    snapshot["aborted_clients_max"] = get_single_value(
        samples, "mariadb_global_status_aborted_clients"
    )
    snapshot["aborted_connects_max"] = get_single_value(
        samples, "mariadb_global_status_aborted_connects"
    )
    return snapshot


def assess(snapshot: Dict[str, object]) -> List[str]:
    """Produce human-readable warnings based on a current snapshot."""
    warnings: List[str] = []

    up = snapshot.get("mariadb_up_max")
    if up is not None and up < 1:
        warnings.append(f"CRITICAL: mariadb_up_max={up} (service appears down or scrape failing)")

    for disk in snapshot.get("disk", []):
        pct = float(disk["utilization_pct"])
        server = disk["server_name"]
        purpose = disk["disk_purpose"]
        if pct >= 95:
            warnings.append(f"CRITICAL: Disk nearly full: {server} {purpose} {pct:.2f}% used")
        elif pct >= 90:
            warnings.append(f"SEVERE: Disk high: {server} {purpose} {pct:.2f}% used")
        elif pct >= 80:
            warnings.append(f"WARN: Disk elevated: {server} {purpose} {pct:.2f}% used")

    cpu = snapshot.get("cpu", {})
    if isinstance(cpu, dict) and "cpu_pct_est" in cpu:
        cpu_pct = float(cpu["cpu_pct_est"])
        if cpu_pct >= 95:
            warnings.append(f"CRITICAL: CPU saturation suspected: ~{cpu_pct:.1f}%")
        elif cpu_pct >= 85:
            warnings.append(f"WARN: CPU high: ~{cpu_pct:.1f}%")

    threads_running = snapshot.get("threads_running_max")
    threads_connected = snapshot.get("threads_connected_max")
    if threads_running is not None and threads_connected is not None and threads_connected > 0:
        ratio = threads_running / threads_connected
        if ratio >= 0.5 and threads_running >= 50:
            warnings.append(
                "WARN: High active thread ratio: "
                f"threads_running={threads_running}, connected={threads_connected} "
                f"(ratio={ratio:.2f})"
            )

    aborted_clients = snapshot.get("aborted_clients_max")
    aborted_connects = snapshot.get("aborted_connects_max")
    if aborted_clients is not None and aborted_clients > 0:
        warnings.append(f"INFO: aborted_clients={aborted_clients} (watch for client disconnects/timeouts)")
    if aborted_connects is not None and aborted_connects > 0:
        warnings.append(f"INFO: aborted_connects={aborted_connects} (watch for auth/network issues)")

    return warnings


def fetch_service_details(api_key: str, service_id: str) -> dict[str, Any] | None:
    """Fetch service metadata from the MariaDB Cloud provisioning API."""
    headers = {"X-API-Key": api_key, "Content-Type": "application/json"}
    try:
        response = requests.get(
            f"{PROVISIONING_SERVICE_URL}/{service_id}",
            headers=headers,
            timeout=30,
        )
        response.raise_for_status()
        data = response.json()
        region = (
            data.get("region")
            or data.get("location")
            or data.get("deployment_region")
        )
        if not region and isinstance(data.get("spec"), dict):
            region = data["spec"].get("region") or data["spec"].get("location")
        if not region and isinstance(data.get("properties"), dict):
            region = data["properties"].get("region") or data["properties"].get("location")
        return {
            "id": data.get("id") or service_id,
            "name": data.get("name"),
            "region": region,
        }
    except requests.RequestException as exc:
        logger.debug("Failed to fetch service details for %s: %s", service_id, exc)
        return None


def fetch_service_region(api_key: str, service_id: str) -> str | None:
    """Backwards-compatible helper returning the deployment/observability region."""
    details = fetch_service_details(api_key, service_id)
    if not details:
        return None
    return details.get("region")


def map_deployment_region_to_observability_region(deployment_region: str) -> str:
    """Map a MariaDB Cloud deployment region to the closest observability region."""
    region_lower = deployment_region.lower()

    if any(token in region_lower for token in ("europe", "westeurope", "northeurope", "uk", "france", "germany")):
        return "europe-west1"
    if any(token in region_lower for token in ("asia", "southeast", "japan", "korea", "australia", "india")):
        return "asia-southeast1"
    return "us-central1"


def normalize_observability_region(region: str | None) -> str:
    """Return a valid observability region, mapping deployment regions when needed."""
    if not region:
        return "us-central1"
    normalized = region.lower().replace("_", "-")
    if normalized in VALID_OBSERVABILITY_REGIONS:
        return normalized
    return map_deployment_region_to_observability_region(region)


def infer_namespace_from_db_host() -> str | None:
    """Extract the MariaDB Cloud service ID from DB_HOST."""
    try:
        db_cfg = DBConfig.from_env()
    except Exception:
        return None
    match = re.search(r"(dbp[a-z0-9]+)", db_cfg.host.lower())
    return match.group(1) if match else None


def resolve_observability_context(
    *,
    namespace: str | None = None,
    service_name: str | None = None,
    region: str | None = None,
    api_key: str | None = None,
) -> tuple[ObservabilityContext | None, str | None]:
    """Resolve namespace, service name, and observability region."""
    cloud_cfg = MariaDBCloudConfig.from_env()
    api_key = api_key or cloud_cfg.api_key

    resolved_namespace = namespace or infer_namespace_from_db_host() or cloud_cfg.service_id
    if not resolved_namespace:
        return None, (
            "Cannot determine namespace (service_id). Provide namespace or set "
            "MARIADB_CLOUD_SERVICE_ID / DB_HOST."
        )

    details = fetch_service_details(api_key, resolved_namespace)
    resolved_service_name = service_name or (details or {}).get("name")
    if not resolved_service_name:
        return None, (
            f"Cannot determine service name for {resolved_namespace}. "
            "Provide service_name or verify provisioning API access."
        )

    if region:
        resolved_region = normalize_observability_region(region)
    else:
        deployment_region = (details or {}).get("region")
        resolved_region = normalize_observability_region(deployment_region)

    return (
        ObservabilityContext(
            namespace=resolved_namespace,
            service_name=resolved_service_name,
            region=resolved_region,
            deployment_region=(details or {}).get("region"),
        ),
        None,
    )


def choose_step_seconds(hours: int, requested_step: int | None = None) -> int:
    """Pick a range step that keeps point counts reasonable."""
    if requested_step and requested_step > 0:
        return requested_step
    if hours <= 1:
        return 60
    if hours <= 6:
        return 300
    if hours <= 24:
        return 900
    return 3600


def summarize_range_values(values: list[list[Any]]) -> dict[str, Any]:
    """Summarize a Prometheus matrix value series."""
    numeric = [float(point[1]) for point in values if len(point) >= 2]
    if not numeric:
        return {"point_count": len(values), "available": False}

    first = numeric[0]
    last = numeric[-1]
    summary = {
        "available": True,
        "point_count": len(numeric),
        "first": first,
        "last": last,
        "min": min(numeric),
        "max": max(numeric),
        "avg": sum(numeric) / len(numeric),
        "delta": last - first,
    }
    if len(values) >= 2:
        summary["start_time"] = datetime.fromtimestamp(float(values[0][0]), tz=UTC).isoformat()
        summary["end_time"] = datetime.fromtimestamp(float(values[-1][0]), tz=UTC).isoformat()
    return summary


def summarize_matrix_result(payload: dict[str, Any]) -> list[dict[str, Any]]:
    """Summarize all series in a Prometheus matrix response."""
    data = payload.get("data") or {}
    results = data.get("result") or []
    summarized: list[dict[str, Any]] = []
    for series in results:
        metric = series.get("metric") or {}
        values = series.get("values") or []
        summarized.append(
            {
                "metric": metric.get("__name__"),
                "labels": {k: v for k, v in metric.items() if k != "__name__"},
                "summary": summarize_range_values(values),
            }
        )
    return summarized


def summarize_vector_result(payload: dict[str, Any]) -> list[dict[str, Any]]:
    """Summarize all samples in a Prometheus vector response."""
    data = payload.get("data") or {}
    results = data.get("result") or []
    summarized: list[dict[str, Any]] = []
    for sample in results:
        metric = sample.get("metric") or {}
        value = sample.get("value") or []
        numeric = float(value[1]) if len(value) >= 2 else None
        summarized.append(
            {
                "metric": metric.get("__name__"),
                "labels": {k: v for k, v in metric.items() if k != "__name__"},
                "value": numeric,
                "timestamp": datetime.fromtimestamp(float(value[0]), tz=UTC).isoformat()
                if len(value) >= 2
                else None,
            }
        )
    return summarized


def _catalog_history_promql(metric_key: str, service_name: str) -> str | None:
    entry = METRIC_CATALOG.get(metric_key) or {}
    template = entry.get("history_promql")
    if not template:
        return None
    return template.format(service_name=service_name)


def _snapshot_value_for_catalog_metric(
    metric_key: str,
    snapshot: dict[str, Any],
) -> dict[str, Any] | None:
    entry = METRIC_CATALOG.get(metric_key) or {}
    if entry.get("snapshot_only"):
        purpose = entry.get("disk_purpose")
        if not purpose:
            return None
        for disk in snapshot.get("disk", []):
            if disk.get("disk_purpose") == purpose:
                return {
                    "value": float(disk["utilization_pct"]),
                    "unit": entry.get("unit", "percent"),
                    "source": "metrics_snapshot",
                }
        return None

    metric_name = entry.get("snapshot_metric")
    if metric_name == "mariadb_server_cpu":
        cpu = snapshot.get("cpu")
        if isinstance(cpu, dict) and "cpu_pct_est" in cpu:
            return {
                "value": float(cpu["cpu_pct_est"]),
                "unit": entry.get("unit", "percent"),
                "source": "metrics_snapshot",
            }
        return None

    mapping = {
        "threads_connected": "threads_connected_max",
        "threads_running": "threads_running_max",
        "mariadb_up": "mariadb_up_max",
    }
    snapshot_key = mapping.get(metric_key)
    if snapshot_key and snapshot.get(snapshot_key) is not None:
        return {
            "value": float(snapshot.get(snapshot_key)),
            "unit": entry.get("unit", "count"),
            "source": "metrics_snapshot",
        }
    return None


def fetch_catalog_metric_history(
    *,
    api_key: str,
    context: ObservabilityContext,
    metric_keys: list[str],
    hours: int,
    step_seconds: int | None = None,
) -> dict[str, Any]:
    """Fetch historical summaries for curated metrics."""
    end = datetime.now(UTC)
    start = end - timedelta(hours=hours)
    step = choose_step_seconds(hours, step_seconds)
    history: dict[str, Any] = {
        "hours": hours,
        "step_seconds": step,
        "start_time": start.isoformat(),
        "end_time": end.isoformat(),
        "metrics": {},
    }

    for metric_key in metric_keys:
        entry = METRIC_CATALOG.get(metric_key)
        if not entry:
            history["metrics"][metric_key] = {"available": False, "message": "Unknown metric key"}
            continue

        promql = _catalog_history_promql(metric_key, context.service_name)
        if not promql:
            history["metrics"][metric_key] = {
                "available": False,
                "label": entry.get("label", metric_key),
                "message": "Historical series not available for this metric; use current snapshot instead.",
                "snapshot_only": True,
            }
            continue

        try:
            payload = query_prometheus_range(
                api_key,
                context.region,
                promql,
                start=start,
                end=end,
                step_seconds=step,
            )
            series = summarize_matrix_result(payload)
            history["metrics"][metric_key] = {
                "available": bool(series),
                "label": entry.get("label", metric_key),
                "promql": promql,
                "unit": entry.get("unit"),
                "series": series,
            }
        except requests.RequestException as exc:
            history["metrics"][metric_key] = {
                "available": False,
                "label": entry.get("label", metric_key),
                "promql": promql,
                "message": f"Failed to fetch history: {exc}",
            }

    return history


def get_mariadb_cloud_observability_snapshot_impl(
    namespace: str | None = None,
    service_name: str | None = None,
    server_name: str | None = None,
    region: str | None = None,
    hours: int | None = None,
    metric_names: list[str] | None = None,
    step_seconds: int | None = None,
) -> dict[str, Any]:
    """Core implementation for current snapshot plus optional curated history."""
    try:
        context, error = resolve_observability_context(
            namespace=namespace,
            service_name=service_name,
            region=region,
        )
        if error or not context:
            return {
                "available": False,
                "snapshot": None,
                "history": None,
                "warnings": [],
                "source": None,
                "message": error or "Unable to resolve observability context.",
            }

        cloud_cfg = MariaDBCloudConfig.from_env()
        text = fetch_metrics(
            cloud_cfg.api_key,
            context.region,
            service_name=context.service_name,
        )
        all_samples = parse_prometheus_text(text)
        filtered = filter_samples(
            all_samples,
            namespace=context.namespace,
            service_name=context.service_name,
            server_name=server_name,
        )
        latest_samples = list(latest_by_series(filtered).values())
        snapshot = build_health_snapshot(latest_samples)
        warnings = assess(snapshot)

        selected_metrics = metric_names or list(METRIC_CATALOG.keys())
        history = None
        if hours is not None and hours > 0:
            bounded_hours = max(1, min(hours, MAX_HISTORY_HOURS))
            history = fetch_catalog_metric_history(
                api_key=cloud_cfg.api_key,
                context=context,
                metric_keys=selected_metrics,
                hours=bounded_hours,
                step_seconds=step_seconds,
            )

        return {
            "available": True,
            "snapshot": snapshot,
            "history": history,
            "warnings": warnings,
            "source": "mariadb_cloud_observability_api",
            "message": None,
            "namespace": context.namespace,
            "service_name": context.service_name,
            "region": context.region,
            "catalog_metrics": list(METRIC_CATALOG.keys()),
        }
    except requests.HTTPError as exc:
        logger.debug("HTTP error fetching observability metrics: %s", exc)
        return {
            "available": False,
            "snapshot": None,
            "history": None,
            "warnings": [],
            "source": None,
            "message": f"HTTP error fetching observability metrics: {exc}. Check API key and service access.",
        }
    except requests.RequestException as exc:
        logger.debug("Request error fetching observability metrics: %s", exc)
        return {
            "available": False,
            "snapshot": None,
            "history": None,
            "warnings": [],
            "source": None,
            "message": f"Request failed: {exc}. Check network connectivity and API key.",
        }
    except Exception as exc:
        logger.debug("Error fetching observability snapshot: %s", exc, exc_info=True)
        return {
            "available": False,
            "snapshot": None,
            "history": None,
            "warnings": [],
            "source": None,
            "message": f"Error fetching observability snapshot: {exc}",
        }


def query_mariadb_cloud_observability_metrics_impl(
    query: str,
    *,
    namespace: str | None = None,
    service_name: str | None = None,
    region: str | None = None,
    hours: int | None = None,
    step_seconds: int | None = None,
    eval_time: datetime | None = None,
) -> dict[str, Any]:
    """Run a custom PromQL instant or range query against MariaDB Cloud observability."""
    try:
        context, error = resolve_observability_context(
            namespace=namespace,
            service_name=service_name,
            region=region,
        )
        if error or not context:
            return {"available": False, "message": error or "Unable to resolve observability context."}

        cloud_cfg = MariaDBCloudConfig.from_env()
        if hours is not None and hours > 0:
            bounded_hours = max(1, min(hours, MAX_HISTORY_HOURS))
            end = datetime.now(UTC)
            start = end - timedelta(hours=bounded_hours)
            step = choose_step_seconds(bounded_hours, step_seconds)
            payload = query_prometheus_range(
                cloud_cfg.api_key,
                context.region,
                query,
                start=start,
                end=end,
                step_seconds=step,
            )
            return {
                "available": True,
                "query_type": "range",
                "query": query,
                "hours": bounded_hours,
                "step_seconds": step,
                "namespace": context.namespace,
                "service_name": context.service_name,
                "region": context.region,
                "series": summarize_matrix_result(payload),
                "raw_status": payload.get("status"),
            }

        payload = query_prometheus_instant(
            cloud_cfg.api_key,
            context.region,
            query,
            eval_time=eval_time,
        )
        return {
            "available": True,
            "query_type": "instant",
            "query": query,
            "namespace": context.namespace,
            "service_name": context.service_name,
            "region": context.region,
            "samples": summarize_vector_result(payload),
            "raw_status": payload.get("status"),
        }
    except requests.RequestException as exc:
        return {"available": False, "message": f"Prometheus query failed: {exc}"}
    except Exception as exc:
        return {"available": False, "message": f"Error running observability query: {exc}"}


@function_tool
def get_mariadb_cloud_observability_snapshot(
    namespace: str | None = None,
    service_name: str | None = None,
    server_name: str | None = None,
    region: str | None = None,
    hours: int | None = None,
    metric_names: list[str] | None = None,
    step_seconds: int | None = None,
) -> dict[str, Any]:
    """
    Get MariaDB Cloud observability metrics: current snapshot and optional historical trends.

    Current snapshot (/observability/v2/metrics):
    - CPU usage, disk utilization (data/logs), threads, aborted connections

    Historical trends (/observability/v2/query_range) when hours is set:
    - threads_connected, threads_running, slow_queries, replication lag, and more
    - CPU and disk utilization are snapshot-only (not stored in the historical TSDB)

    Requires MARIADB_CLOUD_API_KEY. Namespace defaults to DB_HOST service ID, then
    MARIADB_CLOUD_SERVICE_ID.
    The metrics API `service` filter uses the provisioning service *name*, resolved automatically.

    Args:
        namespace: MariaDB Cloud service ID label (e.g. dbpgp26780910)
        service_name: Provisioning service name (e.g. my-service). Auto-resolved when omitted.
        server_name: Optional server_name label filter for snapshot metrics
        region: Observability region (us-central1, europe-west1, asia-southeast1)
        hours: When set, include historical summaries for curated metrics over this window
        metric_names: Optional subset of catalog keys (cpu, threads_connected, slow_queries, ...)
        step_seconds: Optional range query step size in seconds
    """
    return get_mariadb_cloud_observability_snapshot_impl(
        namespace=namespace,
        service_name=service_name,
        server_name=server_name,
        region=region,
        hours=hours,
        metric_names=metric_names,
        step_seconds=step_seconds,
    )


@function_tool
def query_mariadb_cloud_observability_metrics(
    query: str,
    namespace: str | None = None,
    service_name: str | None = None,
    region: str | None = None,
    hours: int | None = None,
    step_seconds: int | None = None,
) -> dict[str, Any]:
    """
    Run a custom PromQL query against MariaDB Cloud observability.

    Uses /observability/v2/query for instant queries (hours omitted) or
    /observability/v2/query_range when hours is provided.

    Example instant query:
        max(mariadb_global_status_threads_connected{mariadb="my-service"})

    Example range query (set hours=6):
        max(mariadb_global_status_slow_queries{mariadb="my-service"})

    Prefer get_mariadb_cloud_observability_snapshot for standard health metrics.
    """
    return query_mariadb_cloud_observability_metrics_impl(
        query=query,
        namespace=namespace,
        service_name=service_name,
        region=region,
        hours=hours,
        step_seconds=step_seconds,
    )
