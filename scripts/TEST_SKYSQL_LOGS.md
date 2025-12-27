# Testing SkySQL API Error Log Integration

This guide explains how to test the SkySQL API error log integration.

## Prerequisites

1. **SkySQL API Key**: 
   - Generate an API key at https://id.mariadb.com/account/api/
   - Add it to your `.env` file:
     ```bash
     SKYSQL_API_KEY=your_api_key_here
     ```

2. **Service ID**: 
   - You need a SkySQL service ID to test with
   - You can find it in the SkySQL portal or from your database hostname
   - Example: `dbpgp29990659` (from hostname `dbpgp29990659.sysp0000.db2.skysql.com`)

3. **Optional Configuration**:
   ```bash
   # Optional - defaults to https://api.skysql.com/observability/v2/logs
   SKYSQL_LOG_API_URL=https://api.skysql.com/observability/v2/logs
   ```

## Test Script

Use the test script to verify the integration:

```bash
cd /Users/jagsramnarayan-mariadb/Documents/skysql/develop/python_programs
source .venv/bin/activate
cd mariadb_db_agents

# Basic test with service_id
python scripts/test_skysql_error_logs.py --service-id <your_service_id>

# Test with custom time range (last 48 hours)
python scripts/test_skysql_error_logs.py --service-id <your_service_id> --hours 48

# Test API connection only (quick test)
python scripts/test_skysql_error_logs.py --service-id <your_service_id> --test-api-only

# Skip full integration test (faster)
python scripts/test_skysql_error_logs.py --service-id <your_service_id> --skip-full-test
```

## Test Steps

The test script performs the following tests:

1. **Configuration Test**: Verifies `SKYSQL_API_KEY` is set
2. **API Connection Test**: Tests authentication and fetches log info
3. **Log Download Test**: Downloads log archive from SkySQL API
4. **Log Extraction Test**: Extracts error log lines from the archive
5. **Full Integration Test**: Tests the complete `tail_error_log_file` function

## Expected Output

```
================================================================================
SkySQL API Error Log Integration Test
================================================================================

================================================================================
Test 1: SkySQL API Configuration
================================================================================

✅ API Key: ********abc12345
✅ API URL: https://api.skysql.com/observability/v2/logs

================================================================================
Test 2: SkySQL API Connection
================================================================================

Service ID: dbpgp29990659
Time range: 2025-12-22T12:00:00Z to 2025-12-23T12:00:00Z

Fetching log info...
✅ Successfully connected to SkySQL API
✅ Found 3 log file(s)
   Log IDs: ['log-id-1', 'log-id-2', 'log-id-3']

...
```

## Testing with Incident Triage Agent

Once the API integration is verified, test it with the Incident Triage Agent:

```bash
# Run the agent with service_id
python -m mariadb_db_agents.cli.main incident-triage --service-id <your_service_id> --max-turns 30
```

The agent will:
1. Fetch error logs from SkySQL API
2. Extract error patterns
3. Analyze them along with database health metrics
4. Provide incident triage report

## Troubleshooting

### Error: "SkySQL API key not set"
- Make sure `SKYSQL_API_KEY` is set in your `.env` file
- Check that you're in the correct directory when running the script

### Error: "Unexpected response code 401"
- Verify your API key is valid
- Check that the API key has permissions to access logs
- Try regenerating the API key

### Error: "No error-log files available"
- Check that the service_id is correct
- Verify that error logs exist for the time range
- Try increasing the time range with `--hours 48` or `--hours 168` (1 week)

### Error: "Total size of error-log files exceeds maximum"
- The logs are too large (>10MB)
- Review logs in the SkySQL portal instead
- Or adjust the time range to a smaller window

### Error: Connection timeout
- Check your internet connection
- Verify the API URL is correct
- The default URL is `https://api.skysql.com/observability/v2/logs`
- For internal deployments, you may need to set `SKYSQL_LOG_API_URL`

## Manual Testing

You can also test the API manually using curl:

```bash
# Set your API key
export SKYSQL_API_KEY="your_api_key_here"

# Get log info
curl -X GET "https://api.skysql.com/observability/v2/logs?logType=error-log&fromDate=2025-12-22T00:00:00Z&toDate=2025-12-23T00:00:00Z" \
  -H "X-API-Key: $SKYSQL_API_KEY" \
  -H "Content-Type: application/json"
```

## Next Steps

After successful testing:
1. Use the Incident Triage Agent with `--service-id` parameter
2. Monitor error logs regularly
3. Set up automated error log analysis if needed


