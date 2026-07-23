from __future__ import annotations

from mariadb_db_agents.common.config import MariaDBCloudConfig
from mariadb_db_agents.ui_api import config_service


def test_mariadb_cloud_config_uses_new_environment_names(monkeypatch):
    monkeypatch.setenv("MARIADB_CLOUD_API_KEY", "cloud-key")
    monkeypatch.setenv("MARIADB_CLOUD_SERVICE_ID", "dbpgp123")
    monkeypatch.setenv(
        "MARIADB_CLOUD_LOG_API_URL",
        "https://api.skysql.com/observability/v2/logs",
    )

    config = MariaDBCloudConfig.from_env()

    assert config.api_key == "cloud-key"
    assert config.service_id == "dbpgp123"
    assert config.api_url.endswith("/observability/v2/logs")


def test_config_service_exposes_and_redacts_mariadb_cloud_keys(monkeypatch):
    monkeypatch.setattr(
        config_service,
        "_read_env_map",
        lambda: {
            "MARIADB_CLOUD_API_KEY": "secret",
            "MARIADB_CLOUD_SERVICE_ID": "dbpgp123",
        },
    )

    values = config_service.get_env_values(redact_secrets=True)

    assert values["MARIADB_CLOUD_API_KEY"] == config_service.SECRET_MASK
    assert values["MARIADB_CLOUD_SERVICE_ID"] == "dbpgp123"
