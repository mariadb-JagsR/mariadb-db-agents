# Database configuration (MariaDB Cloud)

## Set credentials in `.env`

Do not commit real passwords or hosts to the repository. Copy the template and edit locally:

```bash
cd mariadb_db_agents
cp .env.example .env
```

Set at least:

- `DB_HOST` — your MariaDB Cloud hostname (often `*.skysql.com`; the service hostname retains the `skysql.com` domain)
- `DB_PORT` — typically `3306`
- `DB_USER` — database user
- `DB_PASSWORD` — database password
- `DB_DATABASE` — database name (often `mysql` for admin-style connections)

See the main [README.md](README.md) for optional MariaDB Cloud API variables (`MARIADB_CLOUD_API_KEY`, etc.).

## SSL (MariaDB Cloud)

For MariaDB Cloud hosts, SSL with certificate verification is applied automatically when the hostname matches the retained `skysql.com` service domain (see `common/db_client.py`). Other hosts keep the previous non-SSL behavior for local compatibility.

## Test connection

```bash
source ../.venv/bin/activate   # or your venv path
python -c "from mariadb_db_agents.common.config import DBConfig; from mariadb_db_agents.common.db_client import run_readonly_query; DBConfig.from_env(); result = run_readonly_query('SELECT 1 as test', database='mysql'); print('Connection successful!', result)"
```

(Adjust the import path if you run from a layout where the package root differs.)
