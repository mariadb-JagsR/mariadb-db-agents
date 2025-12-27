# Update Database Configuration

## New Database Credentials

Update your `.env` file with these values:

```bash
DB_HOST=dbpgp29990659.sysp0000.db2.skysql.com
DB_PORT=3306
DB_USER=dbpgp29990659
DB_PASSWORD=aMWXUTkE3FYX!5rqCr3Lspghe
DB_DATABASE=mysql
```

## SSL Configuration

The new database requires SSL with server certificate verification. The `db_client.py` has been updated to automatically:
- Enable SSL for SkySQL hosts (detected by `skysql.com` in hostname)
- Verify server certificates (`ssl_verify_cert=True`)
- Verify server identity (`ssl_verify_identity=True`)

## Quick Update Command

```bash
cd mariadb_db_agents
cat >> .env << 'EOF'

# New database (with SSL)
DB_HOST=dbpgp29990659.sysp0000.db2.skysql.com
DB_PORT=3306
DB_USER=dbpgp29990659
DB_PASSWORD=aMWXUTkE3FYX!5rqCr3Lspghe
DB_DATABASE=mysql
EOF
```

Or manually edit `.env` and update the DB_* values.

## Test Connection

After updating, test the connection:

```bash
source ../.venv/bin/activate
python -c "from common.config import DBConfig; from common.db_client import run_readonly_query; cfg = DBConfig.from_env(); result = run_readonly_query('SELECT 1 as test', database='mysql'); print('Connection successful!', result)"
```

## What Changed

1. **SSL Support**: `db_client.py` now automatically enables SSL with certificate verification for SkySQL hosts
2. **Certificate Verification**: Server certificates are now verified (matching `--ssl-verify-server-cert` behavior)
3. **Backward Compatible**: Non-SkySQL hosts still use `ssl_disabled=True` for compatibility


