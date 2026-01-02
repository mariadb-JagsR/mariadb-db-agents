#!/usr/bin/env python3
"""
SkySQL Observability "current snapshot" via /observability/v2/metrics

Goal:
  1) Fetch all metrics
  2) Filter to a specific namespace (service id / namespace label)
  3) Compute key health signals (disk %, cpu if present, connection pressure, error indicators)

Notes:
  - This reads "current" metrics only (Prometheus text exposition format).
  - It does not depend on query_range (historical storage).
"""

from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass
from typing import Dict, Iterable, List, Optional, Tuple
import requests


@dataclass(frozen=True)
class Sample:
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
    # Some SkySQL topologies may not expose mariadb_server_cpu historically, but /metrics may show it live.
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


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--api-key", required=True, help="SkySQL Observability API key (skysql....)")
    ap.add_argument("--region", required=True, choices=["us-central1", "europe-west1", "asia-southeast1"])
    ap.add_argument("--namespace", required=True, help='Namespace label (often the SkySQL service-id like "dbpgp40039323")')
    ap.add_argument("--service-name", default=None, help='Optional service_name label filter (e.g., "jags-dont-delete-2")')
    ap.add_argument("--server-name", default=None, help='Optional server_name label filter (e.g., "...-mdb-ms-0")')
    args = ap.parse_args()

    text = fetch_metrics(args.api_key, args.region)
    all_samples = parse_prometheus_text(text)

    filtered = filter_samples(all_samples, namespace=args.namespace, service_name=args.service_name, server_name=args.server_name)

    # De-dupe by series; keep latest
    latest = latest_by_series(filtered)
    latest_samples = list(latest.values())

    snapshot = build_health_snapshot(latest_samples)
    warnings = assess(snapshot)

    # Pretty-ish output without extra deps
    print("\n=== SkySQL Observability Snapshot ===")
    print(f"namespace={args.namespace} service_name={args.service_name or '*'} server_name={args.server_name or '*'}")
    print(f"samples={len(latest_samples)} (latest per series)\n")

    print("Up:", snapshot.get("mariadb_up_max"))
    print("Threads connected (max):", snapshot.get("threads_connected_max"))
    print("Threads running (max):", snapshot.get("threads_running_max"))
    print("Aborted clients (max):", snapshot.get("aborted_clients_max"))
    print("Aborted connects (max):", snapshot.get("aborted_connects_max"))

    print("\nDisk utilization:")
    disks = snapshot.get("disk", [])
    if disks:
        for d in disks:
            print(
                f"  {d['server_name']:35s} {d['disk_purpose']:5s} "
                f"{d['utilization_pct']:6.2f}%  used={d['used_bytes']:.0f} cap={d['capacity_bytes']:.0f}"
            )
    else:
        print("  (no volume stats found for this namespace filter)")

    print("\nCPU:")
    print(snapshot.get("cpu"))

    print("\nWarnings:")
    if warnings:
        for w in warnings:
            print(" -", w)
    else:
        print(" (none)")

    print("")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except requests.HTTPError as e:
        print(f"HTTP error: {e}", file=sys.stderr)
        returncode = 2
        raise SystemExit(returncode)
    except requests.RequestException as e:
        print(f"Request failed: {e}", file=sys.stderr)
        returncode = 2
        raise SystemExit(returncode)
