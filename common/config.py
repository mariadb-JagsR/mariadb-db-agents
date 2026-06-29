# src/common/config.py
from dataclasses import dataclass
import os
from pathlib import Path

from dotenv import load_dotenv

# Always load the package's .env (mariadb_db_agents/.env), not the shell cwd — otherwise
# DB_DATABASE and other values look "stuck" when the API/CLI is started from a parent path.
_ENV_FILE = Path(__file__).resolve().parent.parent / ".env"
if _ENV_FILE.is_file():
    load_dotenv(_ENV_FILE)
else:
    load_dotenv()


@dataclass
class OpenAIConfig:
    api_key: str
#    model: str = "gpt-4.1-mini"  # or "gpt-4o", change as needed
    model: str = "gpt-5.2"  # or "gpt-4o", change as needed

    @classmethod
    def from_env(cls) -> "OpenAIConfig":
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise RuntimeError("OPENAI_API_KEY is not set in environment or .env")
        model = os.getenv("OPENAI_MODEL", cls.model)
        return cls(api_key=api_key, model=model)


@dataclass
class DBConfig:
    host: str
    port: int
    user: str
    password: str
    database: str

    @classmethod
    def from_env(cls) -> "DBConfig":
        host = os.getenv("DB_HOST")
        user = os.getenv("DB_USER")
        password = os.getenv("DB_PASSWORD")
        database = os.getenv("DB_DATABASE")
        port = int(os.getenv("DB_PORT", "3306"))

        missing = [name for name, val in [
            ("DB_HOST", host),
            ("DB_USER", user),
            ("DB_PASSWORD", password),
            ("DB_DATABASE", database),
        ] if not val]

        if missing:
            raise RuntimeError(f"Missing DB config env vars: {', '.join(missing)}")

        # Strip so CRLF/accidental spaces in .env or shell exports don't break DNS (2005)
        host = host.strip()
        user = user.strip()
        database = database.strip()

        return cls(
            host=host,
            port=port,
            user=user,
            password=password,
            database=database,
        )


@dataclass
class SkySQLConfig:
    """Configuration for SkySQL API access using API key."""
    api_key: str
    api_url: str
    service_id: str | None = None

    @classmethod
    def from_env(cls) -> "SkySQLConfig":
        api_key = os.getenv("SKYSQL_API_KEY")
        api_url = os.getenv(
            "SKYSQL_LOG_API_URL",
            "https://api.skysql.com/observability/v2/logs"
        )
        service_id = os.getenv("SKYSQL_SERVICE_ID")

        if not api_key:
            raise RuntimeError(
                "SkySQL API key not set. Set SKYSQL_API_KEY in environment or .env file. "
                "You can generate an API key at https://id.mariadb.com/account/api/"
            )

        return cls(
            api_key=api_key,
            api_url=api_url,
            service_id=service_id,
        )

