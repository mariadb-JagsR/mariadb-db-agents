from __future__ import annotations

from datetime import timedelta
from types import SimpleNamespace

import pytest
from dateutil import parser

from mariadb_db_agents.common import config, db_client


def _mock_cloud_log_api(monkeypatch: pytest.MonkeyPatch) -> dict[str, str]:
    captured: dict[str, str] = {}
    monkeypatch.setattr(
        config.MariaDBCloudConfig,
        "from_env",
        classmethod(
            lambda cls: SimpleNamespace(
                api_key="test-key",
                api_url="https://example.test/logs",
            )
        ),
    )

    def get_info(**kwargs):
        captured["start_time"] = kwargs["start_timestamp"]
        captured["end_time"] = kwargs["end_timestamp"]
        return ["log-1"]

    monkeypatch.setattr(db_client, "_get_mariadb_cloud_logs_info", get_info)
    monkeypatch.setattr(
        db_client,
        "_get_mariadb_cloud_logs_archive",
        lambda **kwargs: b"archive",
    )
    monkeypatch.setattr(
        db_client,
        "_load_mariadb_cloud_errors",
        lambda **kwargs: ["2026-07-23T10:30:00Z [ERROR] test"],
    )
    return captured


def test_cloud_logs_use_explicit_time_range(monkeypatch: pytest.MonkeyPatch) -> None:
    captured = _mock_cloud_log_api(monkeypatch)

    result = db_client.tail_error_log_file(
        service_id="dbp123",
        start_time="2026-07-23T09:00:00-07:00",
        end_time="2026-07-23T11:00:00-07:00",
        extract_patterns=False,
    )

    assert captured == {
        "start_time": "2026-07-23T16:00:00Z",
        "end_time": "2026-07-23T18:00:00Z",
    }
    assert result["start_time"] == captured["start_time"]
    assert result["end_time"] == captured["end_time"]
    assert result["source"] == "mariadb_cloud_api"


def test_cloud_logs_default_to_seven_days(monkeypatch: pytest.MonkeyPatch) -> None:
    captured = _mock_cloud_log_api(monkeypatch)

    db_client.tail_error_log_file(service_id="dbp123", extract_patterns=False)

    start = parser.isoparse(captured["start_time"])
    end = parser.isoparse(captured["end_time"])
    assert end - start == timedelta(days=7)


def test_cloud_logs_reject_reversed_time_range(monkeypatch: pytest.MonkeyPatch) -> None:
    _mock_cloud_log_api(monkeypatch)

    with pytest.raises(ValueError, match="start_time must be before"):
        db_client.tail_error_log_file(
            service_id="dbp123",
            start_time="2026-07-23T12:00:00Z",
            end_time="2026-07-23T10:00:00Z",
        )
