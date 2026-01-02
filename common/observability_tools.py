# common/observability_tools.py
"""
SkySQL Observability tools for fetching CPU, disk, and system metrics.

This module provides tools to access SkySQL observability metrics that aren't
available via SQL, such as CPU usage and disk volume utilization.
"""

from __future__ import annotations

import re
import logging
from typing import Any, Dict, Iterable, List, Optional, Tuple
from dataclasses import dataclass
import requests
from agents import function_tool
from .config import SkySQLConfig, DBConfig

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class Sample:
    """A single metric sample from Prometheus text format."""
    name: str
    labels: Dict[str, str]
    value: float
    ts_ms: Optional[int] = None


METRIC_LINE_RE = re.compile(
    r"""
    ^
    (?P<name>[a-zA-Z_:][a-zA-Z0-9_:]*)       # metric name
    (?:\{(?P<labels>[^}]*)\})?              # optional {labels}
    \s+
    (?P<value>[-+]?(?:\d+\.?\d*|\d*\.?\d+)(?:[eE][-+]?\d+)?)  # value
    (?:\s+(?P<ts>\d+))?                     # optional timestamp (ms in SkySQL output)
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
    for m in LABEL_RE.finditer(label_blob):
        k = m.group(1)
        v = m.group(2)
        # unescape \" and \\ (minimal)
        v = v.replace(r"\\", "\\").replace(r"\"", '"')
        labels[k] = v
    return labels


def parse_prometheus_text(text: str) -> List[Sample]:
    """Parse Prometheus text exposition format into Sample objects."""
    samples: List[Sample] = []
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        m = METRIC_LINE_RE.match(line)
        if not m:
            # ignore anything unexpected rather than failing hard
            continue
        name = m.group("name")
        labels_blob = m.group("labels") or ""
        value_str = m.group("value")
        ts_str = m.group("ts")
        labels = parse_labels(labels_blob)
        try:
            value = float(value_str)
        except ValueError:
            continue
        ts_ms = int(ts_str) if ts_str else None
        samples.append(Sample(name=name, labels=labels, value=value, ts_ms=ts_ms))
    return samples


def fetch_metrics(api_key: str, region: str, timeout_s: int = 30) -> str:
    """Fetch metrics from SkySQL observability API."""
    url = "https://api.skysql.com/observability/v2/metrics"
    headers = {
        "X-API-Key": api_key,
        "X-Observability-Region": region,
        "accept": "text/plain",
    }
    r = requests.get(url, headers=headers, timeout=timeout_s)
    r.raise_for_status()
    return r.text


def filter_samples(
    samples: Iterable[Sample],
    namespace: str,
    service_name: Optional[str] = None,
    server_name: Optional[str] = None,
) -> List[Sample]:
    """Filter samples by namespace, service_name, and server_name."""
    out: List[Sample] = []
    for s in samples:
        if s.labels.get("namespace") != namespace:
            continue
        if service_name and s.labels.get("service_name") != service_name:
            continue
        if server_name and s.labels.get("server_name") != server_name:
            continue
        out.append(s)
    return out


def latest_by_series(samples: Iterable[Sample]) -> Dict[Tuple[str, Tuple[Tuple[str, str], ...]], Sample]:
    """
    For each unique (metric name + full labelset), keep the latest sample by ts_ms if present,
    else keep the last encountered.
    """
    best: Dict[Tuple[str, Tuple[Tuple[str, str], ...]], Sample] = {}
    for s in samples:
        key = (s.name, tuple(sorted(s.labels.items())))
        prev = best.get(key)
        if not prev:
            best[key] = s
            continue
        # prefer higher timestamp if available
        if s.ts_ms is not None and (prev.ts_ms is None or s.ts_ms >= prev.ts_ms):
            best[key] = s
        elif s.ts_ms is None:
            best[key] = s
    return best


def disk_utilization(samples: Iterable[Sample]) -> List[Dict[str, object]]:
    """
    Extract disk utilization from volume stats metrics.
    
    Uses:
      mariadb_server_volume_stats_used_bytes{disk_purpose=..., server_name=..., namespace=...}
      mariadb_server_volume_stats_capacity_bytes{disk_purpose=..., server_name=..., namespace=...}
    
    Returns rows with utilization % per (server_name, disk_purpose).
    """
    used = {}
    cap = {}

    for s in samples:
        if s.name == "mariadb_server_volume_stats_used_bytes":
            key = (s.labels.get("server_name"), s.labels.get("disk_purpose"))
            used[key] = s.value
        elif s.name == "mariadb_server_volume_stats_capacity_bytes":
            key = (s.labels.get("server_name"), s.labels.get("disk_purpose"))
            cap[key] = s.value

    rows: List[Dict[str, object]] = []
    for key, u in used.items():
        c = cap.get(key)
        if not c or c <= 0:
            continue
        server, purpose = key
        pct = (u / c) * 100.0
        rows.append(
            {
                "server_name": server,
                "disk_purpose": purpose,
                "used_bytes": u,
                "capacity_bytes": c,
                "utilization_pct": pct,
                "remaining_bytes": max(c - u, 0.0),
            }
        )
    # sort worst first
    rows.sort(key=lambda r: float(r["utilization_pct"]), reverse=True)
    return rows


def get_single_value(samples: Iterable[Sample], metric: str, label_filter: Dict[str, str] | None = None) -> Optional[float]:
    """
    Return the max value among matching samples (useful when there are 2 pods, etc.).
    You can refine with label_filter like {"server_name": "..."}.
    """
    vals: List[float] = []
    for s in samples:
        if s.name != metric:
            continue
        if label_filter:
            ok = True
            for k, v in label_filter.items():
                if s.labels.get(k) != v:
                    ok = False
                    break
            if not ok:
                continue
        vals.append(s.value)
    return max(vals) if vals else None


def build_health_snapshot(samples: List[Sample]) -> Dict[str, object]:
    """
    Build a health snapshot from metric samples.
    
    Heuristics for a "current snapshot" (no trends):
      - Disk utilization % (data/logs)
      - CPU (if exists)
      - Connections / threads running
      - Aborted clients/connects
    """
    snapshot: Dict[str, object] = {}

    # Disk
    disks = disk_utilization(samples)
    snapshot["disk"] = disks

    # CPU (only if metric exists in this environment)
    cpu = get_single_value(samples, "mariadb_server_cpu")
    if cpu is not None:
        # Interpreting cpu depends on definition; often it's a ratio [0..1] or percent [0..100].
        # We'll infer:
        cpu_pct = cpu * 100.0 if cpu <= 1.5 else cpu
        snapshot["cpu"] = {"raw": cpu, "cpu_pct_est": cpu_pct}
    else:
        snapshot["cpu"] = {"note": "mariadb_server_cpu not present in /metrics for this namespace (skipping)"}

    # MariaDB-level sanity signals (common ones)
    snapshot["mariadb_up_max"] = get_single_value(samples, "mariadb_up")  # should be 1
    snapshot["threads_connected_max"] = get_single_value(samples, "mariadb_global_status_threads_connected")
    snapshot["threads_running_max"] = get_single_value(samples, "mariadb_global_status_threads_running")
    snapshot["aborted_clients_max"] = get_single_value(samples, "mariadb_global_status_aborted_clients")
    snapshot["aborted_connects_max"] = get_single_value(samples, "mariadb_global_status_aborted_connects")

    return snapshot


def assess(snapshot: Dict[str, object]) -> List[str]:
    """
    Produce human-readable warnings based on current snapshot.
    Tune thresholds to your environment.
    """
    warnings: List[str] = []

    # Up
    up = snapshot.get("mariadb_up_max")
    if up is not None and up < 1:
        warnings.append(f"CRITICAL: mariadb_up_max={up} (service appears down or scrape failing)")

    # Disk thresholds
    disks = snapshot.get("disk", [])
    for d in disks:
        pct = float(d["utilization_pct"])
        server = d["server_name"]
        purpose = d["disk_purpose"]
        if pct >= 95:
            warnings.append(f"CRITICAL: Disk nearly full: {server} {purpose} {pct:.2f}% used")
        elif pct >= 90:
            warnings.append(f"SEVERE: Disk high: {server} {purpose} {pct:.2f}% used")
        elif pct >= 80:
            warnings.append(f"WARN: Disk elevated: {server} {purpose} {pct:.2f}% used")

    # CPU thresholds (if present)
    cpu = snapshot.get("cpu", {})
    if isinstance(cpu, dict) and "cpu_pct_est" in cpu:
        cpu_pct = float(cpu["cpu_pct_est"])
        if cpu_pct >= 95:
            warnings.append(f"CRITICAL: CPU saturation suspected: ~{cpu_pct:.1f}%")
        elif cpu_pct >= 85:
            warnings.append(f"WARN: CPU high: ~{cpu_pct:.1f}%")

    # Threads running: crude saturation signal (needs tuning)
    tr = snapshot.get("threads_running_max")
    tc = snapshot.get("threads_connected_max")
    if tr is not None and tc is not None and tc > 0:
        ratio = tr / tc
        if ratio >= 0.5 and tr >= 50:
            warnings.append(f"WARN: High active thread ratio: threads_running={tr}, connected={tc} (ratio={ratio:.2f})")

    # Aborted connects/clients: auth/network trouble signal
    ac = snapshot.get("aborted_clients_max")
    ab = snapshot.get("aborted_connects_max")
    if ac is not None and ac > 0:
        warnings.append(f"INFO: aborted_clients={ac} (watch for client disconnects/timeouts)")
    if ab is not None and ab > 0:
        warnings.append(f"INFO: aborted_connects={ab} (watch for auth/network issues)")

    return warnings


def fetch_service_region(api_key: str, service_id: str) -> str | None:
    """
    Fetch the deployment region for a SkySQL service from the provisioning API.
    
    Args:
        api_key: SkySQL API key
        service_id: Service ID to query
    
    Returns:
        Deployment region string (e.g., "eastus", "westeurope", "southeastasia") or None if not found
    """
    url = f"https://api.skysql.com/provisioning/v1/services/{service_id}"
    headers = {
        "X-API-Key": api_key,
        "Content-Type": "application/json",
    }
    
    try:
        r = requests.get(url, headers=headers, timeout=30)
        r.raise_for_status()
        data = r.json()
        
        # Extract region from service details
        # The region field might be at different levels in the response
        region = data.get("region") or data.get("location") or data.get("deployment_region")
        
        if region:
            return region
        
        # Try nested structures
        if "spec" in data and isinstance(data["spec"], dict):
            region = data["spec"].get("region") or data["spec"].get("location")
            if region:
                return region
        
        if "properties" in data and isinstance(data["properties"], dict):
            region = data["properties"].get("region") or data["properties"].get("location")
            if region:
                return region
        
        logger.warning(f"Could not find region in service details for {service_id}")
        return None
        
    except requests.HTTPError as e:
        logger.debug(f"HTTP error fetching service details: {e}")
        return None
    except requests.RequestException as e:
        logger.debug(f"Request error fetching service details: {e}")
        return None
    except Exception as e:
        logger.debug(f"Error fetching service region: {e}", exc_info=True)
        return None


def map_deployment_region_to_observability_region(deployment_region: str) -> str:
    """
    Map SkySQL deployment region to the closest observability region.
    
    Observability regions:
    - us-central1 (for US regions)
    - europe-west1 (for European regions)
    - asia-southeast1 (for Asia-Pacific regions)
    
    Args:
        deployment_region: SkySQL deployment region (e.g., "eastus", "westeurope", "southeastasia")
    
    Returns:
        Observability region string
    """
    region_lower = deployment_region.lower()
    
    # European regions
    if any(x in region_lower for x in ["europe", "westeurope", "northeurope", "uk", "france", "germany"]):
        return "europe-west1"
    
    # Asia-Pacific regions
    if any(x in region_lower for x in ["asia", "southeast", "japan", "korea", "australia", "india"]):
        return "asia-southeast1"
    
    # Default to US (covers eastus, westus, centralus, etc.)
    return "us-central1"


@function_tool
def get_skysql_observability_snapshot(
    namespace: str | None = None,
    service_name: str | None = None,
    server_name: str | None = None,
    region: str | None = None,
) -> dict[str, Any]:
    """
    Get SkySQL observability snapshot including CPU%, disk utilization, and system metrics.
    
    This tool provides metrics that aren't accessible via SQL:
    - CPU usage percentage
    - Disk volume utilization (data/logs)
    - Threads connected/running
    - Aborted connections/clients
    
    **Important**: This tool requires:
    - SKYSQL_API_KEY environment variable
    - SkySQL service (namespace typically matches service_id)
    - Appropriate region (us-central1, europe-west1, or asia-southeast1)
    
    Args:
        namespace: SkySQL namespace (typically the service_id like "dbpgp40039323").
                  If not provided, will attempt to infer from DB_HOST or use SKYSQL_SERVICE_ID.
        service_name: Optional service_name label filter (e.g., "my-service")
        server_name: Optional server_name label filter (e.g., "...-mdb-ms-0")
        region: SkySQL observability region. If not provided, will fetch service details from
                provisioning API to determine deployment region and map to closest observability region.
                Must be one of: "us-central1", "europe-west1", "asia-southeast1"
    
    Returns:
        Dictionary with:
        - available: True if snapshot was successfully retrieved
        - snapshot: Health snapshot with disk, cpu, threads, aborted connections
        - warnings: List of human-readable warnings based on thresholds
        - source: "skysql_observability_api"
        - message: Error message if unavailable
    """
    try:
        # Get SkySQL config
        skysql_cfg = SkySQLConfig.from_env()
        
        # Determine namespace (service_id)
        if not namespace:
            namespace = skysql_cfg.service_id
            if not namespace:
                # Try to infer from DB host
                try:
                    db_cfg = DBConfig.from_env()
                    # SkySQL service IDs are typically in the hostname
                    # Extract service ID pattern (e.g., "dbpgp40039323" from "dbpgp40039323.sysp0000.db2.skysql.com")
                    import re
                    match = re.search(r'(dbp[a-z0-9]+)', db_cfg.host.lower())
                    if match:
                        namespace = match.group(1)
                    else:
                        return {
                            "available": False,
                            "snapshot": None,
                            "warnings": [],
                            "source": None,
                            "message": "Cannot determine namespace (service_id). Provide namespace parameter or set SKYSQL_SERVICE_ID environment variable.",
                        }
                except Exception as e:
                    return {
                        "available": False,
                        "snapshot": None,
                        "warnings": [],
                        "source": None,
                        "message": f"Cannot determine namespace: {str(e)}. Provide namespace parameter or set SKYSQL_SERVICE_ID environment variable.",
                    }
        
        # Determine region by fetching service details from provisioning API
        if not region:
            try:
                # Fetch the deployment region from the provisioning API
                deployment_region = fetch_service_region(skysql_cfg.api_key, namespace)
                if deployment_region:
                    # Map deployment region to observability region
                    region = map_deployment_region_to_observability_region(deployment_region)
                    logger.debug(f"Mapped deployment region {deployment_region} to observability region {region}")
                else:
                    # Fallback: default to us-central1 if unable to fetch
                    logger.warning(f"Could not fetch service region for {namespace}, defaulting to us-central1")
                    region = "us-central1"
            except Exception as e:
                # Default to us-central1 if unable to fetch
                logger.warning(f"Error fetching service region: {e}, defaulting to us-central1")
                region = "us-central1"
        
        # Validate region
        if region not in ["us-central1", "europe-west1", "asia-southeast1"]:
            return {
                "available": False,
                "snapshot": None,
                "warnings": [],
                "source": None,
                "message": f"Invalid region: {region}. Must be one of: us-central1, europe-west1, asia-southeast1",
            }
        
        # Fetch metrics
        text = fetch_metrics(skysql_cfg.api_key, region)
        all_samples = parse_prometheus_text(text)
        
        # Filter samples
        filtered = filter_samples(
            all_samples,
            namespace=namespace,
            service_name=service_name,
            server_name=server_name,
        )
        
        # De-dupe by series; keep latest
        latest = latest_by_series(filtered)
        latest_samples = list(latest.values())
        
        # Build snapshot
        snapshot = build_health_snapshot(latest_samples)
        warnings = assess(snapshot)
        
        return {
            "available": True,
            "snapshot": snapshot,
            "warnings": warnings,
            "source": "skysql_observability_api",
            "message": None,
            "namespace": namespace,
            "region": region,
        }
        
    except requests.HTTPError as e:
        logger.debug(f"HTTP error fetching observability metrics: {e}")
        return {
            "available": False,
            "snapshot": None,
            "warnings": [],
            "source": None,
            "message": f"HTTP error fetching observability metrics: {str(e)}. Check API key and service access.",
        }
    except requests.RequestException as e:
        logger.debug(f"Request error fetching observability metrics: {e}")
        return {
            "available": False,
            "snapshot": None,
            "warnings": [],
            "source": None,
            "message": f"Request failed: {str(e)}. Check network connectivity and API key.",
        }
    except Exception as e:
        logger.debug(f"Error fetching observability snapshot: {e}", exc_info=True)
        return {
            "available": False,
            "snapshot": None,
            "warnings": [],
            "source": None,
            "message": f"Error fetching observability snapshot: {str(e)}",
        }

