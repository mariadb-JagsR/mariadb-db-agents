# Testing MariaDB Cloud Error-Log Integration

This guide verifies API authentication, error-log discovery, archive download,
and pattern extraction for MariaDB Cloud.

## Prerequisites

Set the MariaDB Cloud API configuration in `.env`:

```bash
MARIADB_CLOUD_API_KEY=your_api_key_here
MARIADB_CLOUD_SERVICE_ID=dbpgp12345678
MARIADB_CLOUD_LOG_API_URL=https://api.skysql.com/observability/v2/logs
```

The API and database hostnames retain the `skysql.com` domain even though the
product is named MariaDB Cloud.

## Run the integration test

```bash
# Verify authentication and discover available error-log archives
python scripts/test_mariadb_cloud_error_logs.py --test-api-only

# Download and inspect the last 24 hours
python scripts/test_mariadb_cloud_error_logs.py

# Use a specific service and time window
python scripts/test_mariadb_cloud_error_logs.py \
  --service-id dbpgp12345678 \
  --hours 48

# Save the structured result
python scripts/test_mariadb_cloud_error_logs.py \
  --output mariadb_cloud_error_logs_result.json
```

If the API authenticates but reports no `error-log` files, the integration is
reachable and the selected service simply has no archived error logs in that
time window.

## Direct API check

```bash
curl -G 'https://api.skysql.com/observability/v2/logs' \
  --data-urlencode 'logType=error-log' \
  --data-urlencode 'fromDate=2026-07-21T00:00:00Z' \
  --data-urlencode 'toDate=2026-07-22T00:00:00Z' \
  -H 'X-API-Key: YOUR_MARIADB_CLOUD_API_KEY'
```

Never commit API keys or generated log archives.
