# MCP Server Setup Guide

Quick setup guide for using MariaDB Database Management Agents in Cursor, Windsurf, and other MCP-compatible IDEs.

## Quick Start

1. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

2. **Configure your IDE** (see below for specific instructions)

3. **Start using agents** in your IDE's chat interface!

## Cursor IDE Setup

### Step 1: Open Cursor Settings

1. Open Cursor Settings (Cmd/Ctrl + ,)
2. Navigate to **"Tools & MCP"** (or search for "MCP" in settings)

### Step 2: Add Server Configuration

In the MCP configuration section, add the following JSON:

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
        "OPENAI_API_KEY": "sk-...",
        "DB_HOST": "your-db-host",
        "DB_PORT": "3306",
        "DB_USER": "your-db-user",
        "DB_PASSWORD": "your-db-password",
        "DB_DATABASE": "your-database"
      }
    }
  }
}
```

### Step 3: Save and Verify

Save the configuration. Cursor will automatically load the MCP server. You may need to restart Cursor if the tools don't appear immediately.

### Step 4: Test

Open Cursor's chat and ask: "Is my database healthy?"

The orchestrator agent should respond with a health check report.

## Windsurf IDE Setup

1. Open Windsurf Settings
2. Navigate to "MCP Servers"
3. Click "Add Server"
4. Configure:
   - **Name**: `mariadb-db-agents`
   - **Command**: `python` (or full path to Python)
   - **Arguments**: `-m`, `mariadb_db_agents.mcp_server.main`
   - **Environment**: Add your database and OpenAI credentials
5. Save and restart Windsurf

## Using Virtual Environments

If you're using a virtual environment, use the full path to the Python interpreter:

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
        "OPENAI_API_KEY": "sk-...",
        "DB_HOST": "your-db-host",
        "DB_PORT": "3306",
        "DB_USER": "your-db-user",
        "DB_PASSWORD": "your-db-password",
        "DB_DATABASE": "your-database"
      }
    }
  }
}
```

## Using .env File

If you prefer to use a `.env` file:

1. Create a `.env` file in your project root with:
   ```
   OPENAI_API_KEY=sk-...
   DB_HOST=your-db-host
   DB_PORT=3306
   DB_USER=your-db-user
   DB_PASSWORD=your-db-password
   DB_DATABASE=your-database
   ```

2. In the MCP configuration, only include `OPENAI_API_KEY` (or omit env entirely if using dotenv auto-loading):
   ```json
   {
     "mcpServers": {
       "mariadb-db-agents": {
         "command": "python",
         "args": ["-m", "mariadb_db_agents.mcp_server.main"],
         "env": {
           "OPENAI_API_KEY": "sk-..."
         }
       }
     }
   }
   ```

## Example Queries

Once set up, try these in your IDE's chat:

- **Health Check**: "Is my database healthy?"
- **Slow Queries**: "Analyze slow queries from the last hour"
- **Running Queries**: "What queries are running right now?"
- **Replication**: "Check replication health"
- **Custom SQL**: "Execute: SELECT COUNT(*) FROM users"

## Troubleshooting

### "Module not found" error

Ensure the package is installed:
```bash
pip install -e .
```

Or ensure Python can find the module:
```bash
python -c "import mariadb_db_agents.mcp_server; print('OK')"
```

### "MCP SDK not installed" error

Install the MCP SDK:
```bash
pip install mcp>=0.9.0
```

### Tools not appearing

1. Restart your IDE
2. Check the MCP server status in IDE settings
3. Verify the configuration JSON is valid
4. Check IDE logs for errors

### Connection errors

1. Verify database credentials
2. Check network connectivity to database
3. Verify OpenAI API key is valid
4. Check IDE console for detailed error messages

## Next Steps

- See [MCP Server README](../mcp_server/README.md) for detailed documentation
- See [Main README](../README.md) for agent capabilities
- See [Orchestrator README](../orchestrator/README.md) for routing logic

