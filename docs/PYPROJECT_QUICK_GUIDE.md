# pyproject.toml Quick Guide

## TL;DR - What It Does

`pyproject.toml` makes your project **installable as a Python package** and creates a **command-line tool**.

## Before vs After

### ❌ Before (Without pyproject.toml):
```bash
# Users had to do this:
cd mariadb_db_agents
python -m mariadb_db_agents.cli.main slow-query --hours 1
```

### ✅ After (With pyproject.toml):
```bash
# Users can do this:
pip install -e .
mariadb-db-agents slow-query --hours 1
```

## Key Sections Explained

### 1. Package Info
```toml
name = "mariadb-db-agents"
version = "0.1.0"
description = "AI-powered agents for MariaDB..."
```
**Like:** Your package's "business card" - name, version, what it does

### 2. Dependencies
```toml
dependencies = [
    "openai-agents>=0.6.0",
    "mysql-connector-python>=9.0.0",
    "python-dotenv>=1.0.1",
]
```
**Like:** Your `requirements.txt` but in a standard format

### 3. CLI Command
```toml
[project.scripts]
mariadb-db-agents = "mariadb_db_agents.cli.main:main"
```
**This creates:** A `mariadb-db-agents` command that anyone can run after installing

### 4. Dev Tools (Optional)
```toml
[project.optional-dependencies]
dev = ["pytest", "black", "flake8"]
```
**Install with:** `pip install -e ".[dev]"` (only for developers)

## How to Use

### For End Users:
```bash
# Clone and install
git clone https://github.com/mariadb-JagsR/mariadb-db-agents.git
cd mariadb-db-agents
pip install -e .

# Now use the command
mariadb-db-agents slow-query --hours 1
```

### For Developers:
```bash
# Install with dev tools
pip install -e ".[dev]"

# Now you have pytest, black, flake8, mypy
pytest
black .
flake8 .
```

## What Gets Installed?

When you run `pip install -e .`:

1. ✅ Installs all dependencies (from `dependencies` section)
2. ✅ Makes `mariadb_db_agents` importable as a package
3. ✅ Creates `mariadb-db-agents` command-line tool
4. ✅ Links to your source code (changes take effect immediately)

## Real Example

**Check if it's installed:**
```bash
pip show mariadb-db-agents
```

**Output:**
```
Name: mariadb-db-agents
Version: 0.1.0
Summary: AI-powered agents for MariaDB database management...
Requires: mysql-connector-python, openai-agents, python-dotenv
```

## Why Both pyproject.toml AND requirements.txt?

| File | Purpose | When to Use |
|------|---------|-------------|
| `pyproject.toml` | Package installation, metadata, CLI commands | `pip install -e .` |
| `requirements.txt` | Simple dependency list | `pip install -r requirements.txt` |

**Best Practice:** Keep both!
- `pyproject.toml` - For proper package installation
- `requirements.txt` - For simple workflows

## Summary

Think of `pyproject.toml` as:
- 📦 **Package definition** (what your package is)
- 🔧 **Installation instructions** (how to install it)
- 🛠️ **Tool configuration** (black, mypy settings)
- 📝 **Metadata** (version, description, license)

It's the modern Python way to package your project!


