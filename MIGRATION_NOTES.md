# Migration Notes

## Restructure Summary

The project has been restructured from `mariadb_slow_query_agent/` to `mariadb_db_agents/` to better reflect its role as a multi-agent platform for database management.

## Key Changes

### Directory Structure
- **Old**: `src/agent.py` (slow query agent at root level)
- **New**: `agents/slow_query/agent.py` (organized by agent type)

### Import Paths
All imports have been updated to use relative imports from the new structure:

**Old imports:**
```python
from .common.config import OpenAIConfig
from .tools import execute_sql
```

**New imports:**
```python
from ...common.config import OpenAIConfig
from .tools import execute_sql
```

### CLI Usage

**Old way:**
```bash
python -m mariadb_slow_query_agent.src.main --service-id X
python -m mariadb_slow_query_agent.src.running_query_agent.main --service-id X
```

**New way (unified CLI):**
```bash
python -m mariadb_db_agents.cli.main slow-query --service-id X
python -m mariadb_db_agents.cli.main running-query --service-id X
```

**New way (direct agent access):**
```bash
python -m mariadb_db_agents.agents.slow_query.main --service-id X
python -m mariadb_db_agents.agents.running_query.main --service-id X
```

## Files Moved

- `src/common/` → `common/`
- `src/agent.py` → `agents/slow_query/agent.py`
- `src/tools.py` → `agents/slow_query/tools.py`
- `src/main.py` → `agents/slow_query/main.py`
- `src/conversation.py` → `agents/slow_query/conversation.py`
- `src/running_query_agent/` → `agents/running_query/`
- Utility scripts → `scripts/`
- Documentation → `docs/`

## New Additions

- `cli/main.py` - Unified CLI entry point
- `__init__.py` files throughout for proper package structure
- Updated README with new structure documentation

## Testing

After migration, verify:
1. Both agents can be run via unified CLI
2. Both agents can be run directly
3. Interactive conversation mode works for both
4. All imports resolve correctly

## Next Steps

1. Test the restructured code
2. Update any CI/CD scripts that reference old paths
3. Update documentation references
4. Consider deprecating old directory (after verification)

