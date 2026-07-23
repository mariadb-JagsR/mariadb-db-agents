from __future__ import annotations

from datetime import UTC, datetime

from mariadb_db_agents.common.observability_tools import (
    METRIC_CATALOG,
    build_health_snapshot,
    choose_step_seconds,
    get_mariadb_cloud_observability_snapshot_impl,
    map_deployment_region_to_observability_region,
    normalize_observability_region,
    parse_prometheus_text,
    query_mariadb_cloud_observability_metrics_impl,
    summarize_matrix_result,
    summarize_range_values,
)


def test_parse_prometheus_text_with_timestamp():
    text = (
        '# HELP mariadb_up MariaDB up\n'
        'mariadb_up{namespace="dbpgp123",service_name="svc-a"} 1 1784781894009\n'
    )
    samples = parse_prometheus_text(text)
    assert len(samples) == 1
    assert samples[0].name == "mariadb_up"
    assert samples[0].labels["namespace"] == "dbpgp123"
    assert samples[0].value == 1.0
    assert samples[0].ts_ms == 1784781894009


def test_build_health_snapshot_cpu_percent():
    text = (
        'mariadb_server_cpu{namespace="dbpgp123",service_name="svc-a",server_name="svc-a-0"} 0.42 1\n'
        'mariadb_server_volume_stats_used_bytes{namespace="dbpgp123",service_name="svc-a",server_name="svc-a-0",disk_purpose="data"} 50 1\n'
        'mariadb_server_volume_stats_capacity_bytes{namespace="dbpgp123",service_name="svc-a",server_name="svc-a-0",disk_purpose="data"} 100 1\n'
    )
    snapshot = build_health_snapshot(parse_prometheus_text(text))
    assert snapshot["cpu"]["cpu_pct_est"] == 42.0
    assert len(snapshot["disk"]) == 1
    assert snapshot["disk"][0]["utilization_pct"] == 50.0


def test_normalize_observability_region_accepts_observability_regions():
    assert normalize_observability_region("us-central1") == "us-central1"
    assert normalize_observability_region("eastus") == "us-central1"
    assert normalize_observability_region("westeurope") == "europe-west1"


def test_map_deployment_region_to_observability_region():
    assert map_deployment_region_to_observability_region("southeastasia") == "asia-southeast1"


def test_choose_step_seconds_scales_with_window():
    assert choose_step_seconds(1) == 60
    assert choose_step_seconds(6) == 300
    assert choose_step_seconds(24) == 900
    assert choose_step_seconds(48) == 3600
    assert choose_step_seconds(6, requested_step=120) == 120


def test_summarize_range_values():
    values = [
        [1700000000, "1"],
        [1700003600, "3"],
        [1700007200, "5"],
    ]
    summary = summarize_range_values(values)
    assert summary["available"] is True
    assert summary["min"] == 1.0
    assert summary["max"] == 5.0
    assert summary["avg"] == 3.0
    assert summary["delta"] == 4.0


def test_summarize_matrix_result():
    payload = {
        "status": "success",
        "data": {
            "resultType": "matrix",
            "result": [
                {
                    "metric": {"__name__": "mariadb_global_status_threads_connected", "mariadb": "svc-a"},
                    "values": [[1700000000, "2"], [1700003600, "4"]],
                }
            ],
        },
    }
    series = summarize_matrix_result(payload)
    assert len(series) == 1
    assert series[0]["metric"] == "mariadb_global_status_threads_connected"
    assert series[0]["summary"]["max"] == 4.0


def test_catalog_contains_snapshot_only_cpu_and_disk():
    assert METRIC_CATALOG["cpu"]["history_promql"] is None
    assert METRIC_CATALOG["disk_data_utilization"]["snapshot_only"] is True
    assert "history_promql" in METRIC_CATALOG["threads_connected"]


def test_query_impl_rejects_missing_context(monkeypatch):
    monkeypatch.setattr(
        "mariadb_db_agents.common.observability_tools.resolve_observability_context",
        lambda **kwargs: (None, "missing context"),
    )
    result = query_mariadb_cloud_observability_metrics_impl('max(up{mariadb="x"})')
    assert result["available"] is False
    assert "missing context" in result["message"]


def test_snapshot_impl_rejects_missing_context(monkeypatch):
    monkeypatch.setattr(
        "mariadb_db_agents.common.observability_tools.resolve_observability_context",
        lambda **kwargs: (None, "missing context"),
    )
    result = get_mariadb_cloud_observability_snapshot_impl()
    assert result["available"] is False
    assert result["snapshot"] is None
