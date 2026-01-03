# MCP Server for MariaDB Database Management Agents

This MCP (Model Context Protocol) server exposes all MariaDB database management agents as tools that can be used in IDEs like Cursor, Windsurf, and other MCP-compatible applications.

## Overview

The MCP server provides access to:
- **Orchestrator Agent**: Intelligent routing to specialized agents (recommended entry point)
- **Slow Query Agent**: Analyze historical slow queries
- **Running Query Agent**: Analyze currently executing queries
- **Incident Triage Agent**: Quick health checks and issue identification
- **Replication Health Agent**: Monitor replication lag and health
- **Database Inspector Agent**: Execute read-only SQL queries

## Installation

1. **Install dependencies** (if not already installed):
   ```bash
   pip install -r requirements.txt
   ```

2. **Verify the MCP server is available**:
   ```bash
   python -m mariadb_db_agents.mcp_server.main --help
   ```
   
   Or if installed as a package:
   ```bash
   mariadb-db-agents-mcp --help
   ```

## Configuration

### For Cursor IDE

1. Open Cursor Settings (Cmd/Ctrl + ,)
2. Navigate to **"Tools & MCP"** (or search for "MCP" in settings)
3. In the MCP configuration section, add the following JSON:

```json
{
  "mcpServers": {
    "mariadb-db-agents": {
      "command": "python",
      "args": [
        "-m",
        "mariadb_db_agents.mcp_server.main"
      ],
      "env": {
        "OPENAI_API_KEY": "your-openai-api-key",
        "DB_HOST": "your-db-host",
        "DB_PORT": "3306",
        "DB_USER": "your-db-user",
        "DB_PASSWORD": "your-db-password",
        "DB_DATABASE": "your-database-name"
      }
    }
  }
}
```

**Alternative**: If you have a `.env` file with your configuration:

```json
{
  "mcpServers": {
    "mariadb-db-agents": {
      "command": "python",
      "args": [
        "-m",
        "mariadb_db_agents.mcp_server.main"
      ],
      "env": {
        "OPENAI_API_KEY": "your-openai-api-key"
      }
    }
  }
}
```

Then ensure your `.env` file is in the project root or set `DOTENV_PATH` environment variable.

**Using virtual environment**: If you're using a virtual environment:

```json
{
  "mcpServers": {
    "mariadb-db-agents": {
      "command": "/path/to/your/venv/bin/python",
      "args": [
        "-m",
        "mariadb_db_agents.mcp_server.main"
      ],
      "env": {
        "OPENAI_API_KEY": "your-openai-api-key",
        "DB_HOST": "your-db-host",
        "DB_PORT": "3306",
        "DB_USER": "your-db-user",
        "DB_PASSWORD": "your-db-password",
        "DB_DATABASE": "your-database-name"
      }
    }
  }
}
```

### For Windsurf IDE

1. Open Windsurf Settings
2. Navigate to "MCP Servers" or "Model Context Protocol"
3. Add a new server with:
   - **Name**: `mariadb-db-agents`
   - **Command**: `python` (or path to your Python interpreter)
   - **Arguments**: `["-m", "mariadb_db_agents.mcp_server.main"]`
   - **Environment Variables**: Add your database and OpenAI API configuration

**Note**: In Cursor, you configure MCP servers directly in Settings → Tools & MCP. No need to manually edit configuration files.

## Environment Variables

The MCP server uses the same environment variables as the CLI:

- `OPENAI_API_KEY`: Your OpenAI API key (required)
- `OPENAI_MODEL`: Model to use (default: `gpt-4o` or as configured)
- `DB_HOST`: MariaDB host address (required)
- `DB_PORT`: MariaDB port (default: 3306)
- `DB_USER`: Read-only database user (required)
- `DB_PASSWORD`: Database password (required)
- `DB_DATABASE`: Database name (required)
- `SKYSQL_API_KEY`: (Optional) SkySQL API key for error log access
- `SKYSQL_SERVICE_ID`: (Optional) SkySQL service ID for error log access
- `SKYSQL_LOG_API_URL`: (Optional) SkySQL log API URL

## Usage

Once configured, you can use the agents directly in your IDE's chat interface:

### Using the Orchestrator (Recommended)

Ask natural language questions:
- "Is my database healthy?"
- "Analyze slow queries from the last hour"
- "What queries are running right now?"
- "Why is my database slow?"
- "Check replication health"

The orchestrator will intelligently route to the appropriate specialized agents.

### Using Individual Agents

You can also call specific agents directly:

**Slow Query Analysis:**
- "Analyze slow queries from the last 3 hours, focus on top 5 patterns"

**Running Query Analysis:**
- "Show me queries running longer than 5 seconds"

**Incident Triage:**
- "Perform a health check"
- "Something's wrong with my database"

**Replication Health:**
- "Check replication health"
- "Is replication lagging?"

**Database Inspector:**
- "Execute: SELECT * FROM information_schema.tables LIMIT 10"
- "What tables are in the database?"

## Troubleshooting

### Server Not Starting

1. **Check Python path**: Ensure the Python interpreter can find the `mariadb_db_agents` package
   ```bash
   python -c "import mariadb_db_agents.mcp_server; print('OK')"
   ```

2. **Check dependencies**: Ensure MCP SDK is installed
   ```bash
   pip install mcp>=0.9.0
   ```

3. **Check environment variables**: Ensure all required environment variables are set

4. **Check logs**: Look for error messages in the IDE's MCP server logs

### Tools Not Appearing

1. **Restart the IDE**: After adding the MCP server configuration, restart Cursor/Windsurf
2. **Check server status**: Look for the MCP server status in IDE settings
3. **Verify configuration**: Ensure the JSON configuration is valid

### Connection Errors

1. **Database connection**: Verify database credentials and network access
2. **OpenAI API**: Verify your OpenAI API key is valid and has credits
3. **Check logs**: Review error messages in the IDE's console or MCP server logs

## Development

To test the MCP server locally:

```bash
# Run the server directly (for testing)
python -m mariadb_db_agents.mcp_server.main
```

The server communicates via stdio (standard input/output), so it's designed to be run by the IDE, not directly.

## Additional Resources

- [MCP Protocol Documentation](https://modelcontextprotocol.io/)
- [Cursor MCP Documentation](https://docs.cursor.com/mcp)
- [Main Project README](../README.md)

