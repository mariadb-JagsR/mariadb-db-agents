# src/common/config.py
from dataclasses import dataclass
import os
from dotenv import load_dotenv

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

        return cls(
            host=host,
            port=port,
            user=user,
            password=password,
            database=database,
        )

