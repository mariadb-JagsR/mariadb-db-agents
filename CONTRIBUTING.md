# Contributing to MariaDB Database Management Agents

Thank you for your interest in contributing! This document provides guidelines and instructions for contributing to the project.

## Getting Started

### Prerequisites

- Python 3.8 or higher
- MariaDB/MySQL database access (for testing)
- OpenAI API key (for agent functionality)
- Git

### Development Setup

1. **Clone the repository**
   ```bash
   git clone https://github.com/mariadb-JagsR/mariadb-db-agents.git
   cd mariadb-db-agents
   ```

2. **Create and activate a virtual environment**
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   # Or install in development mode:
   pip install -e ".[dev]"
   ```

4. **Set up environment variables**
   ```bash
   cp .env.example .env
   # Edit .env with your database credentials and OpenAI API key
   ```

## Project Structure

- `agents/` - Individual agent implementations
  - Each agent has: `agent.py`, `tools.py`, `main.py`, `conversation.py`
- `common/` - Shared utilities and infrastructure
- `cli/` - Unified command-line interface
- `scripts/` - Utility scripts for testing and setup
- `docs/` - Documentation
- `tests/` - Test suite (to be expanded)

## Adding a New Agent

1. **Create agent directory**
   ```bash
   mkdir -p agents/your_agent_name
   ```

2. **Follow the existing pattern**
   - `agent.py` - Define the agent with system prompt and tools
   - `tools.py` - Define agent-specific tools using `@function_tool`
   - `main.py` - CLI entry point for one-time analysis
   - `conversation.py` - Interactive conversation client

3. **Add to unified CLI**
   - Update `cli/main.py` to include your agent
   - Add appropriate command-line arguments

4. **Update documentation**
   - Add agent description to `README.md`
   - Update `docs/HIGH_VALUE_AUTOMATION_OPPORTUNITIES.md` if applicable

5. **Test your agent**
   - Test with real database connections
   - Verify guardrails work correctly
   - Test both CLI and interactive modes

## Code Style

- Follow PEP 8 style guidelines
- Use type hints for function signatures
- Keep functions focused and single-purpose
- Add docstrings to all public functions and classes
- Maximum line length: 100 characters

## Testing

Before submitting a pull request:

1. **Test your changes**
   ```bash
   # Run tests (when test suite is expanded)
   pytest
   ```

2. **Test manually**
   - Run the agent with your changes
   - Verify it works with real database connections
   - Test edge cases and error handling

3. **Check for linting issues**
   ```bash
   flake8 .
   black --check .
   ```

## Commit Guidelines

- Use clear, descriptive commit messages
- Keep commits focused on a single change
- Reference issue numbers if applicable

Example:
```
feat: Add connection pool analysis agent

- Implement connection pool monitoring
- Add connection leak detection
- Update CLI to include new agent
```

## Pull Request Process

1. **Create a feature branch**
   ```bash
   git checkout -b feature/your-feature-name
   ```

2. **Make your changes**
   - Write clean, well-documented code
   - Add tests if applicable
   - Update documentation

3. **Commit your changes**
   ```bash
   git add .
   git commit -m "feat: Description of your changes"
   ```

4. **Push and create PR**
   ```bash
   git push origin feature/your-feature-name
   ```
   Then create a pull request on GitHub.

5. **PR Review**
   - Address any feedback
   - Ensure all checks pass
   - Update PR description with details

## Agent Development Guidelines

### Safety First

- **All database operations must be read-only**
  - Use `run_readonly_query()` from `common.db_client`
  - Never execute DDL or DML statements
  - Present changes as suggestions only

### Guardrails

- Implement input guardrails to prevent SQL injection
- Implement output guardrails to prevent leaking sensitive data
- Use the guardrail utilities in `common/guardrails.py`

### Tool Design

- Tools should be focused and single-purpose
- Use descriptive names and docstrings
- Handle errors gracefully
- Return structured data (dictionaries) when possible

### System Prompts

- Be specific about the agent's role and capabilities
- Include examples of good analysis
- Emphasize safety and read-only operations
- Reference available tools and their purposes

## Questions?

- Open an issue for bugs or feature requests
- Check existing documentation in `docs/`
- Review existing agent implementations for examples

## License

By contributing, you agree that your contributions will be licensed under the MIT License.

