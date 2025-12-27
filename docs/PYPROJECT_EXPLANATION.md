# Understanding pyproject.toml

## What is pyproject.toml?

`pyproject.toml` is a **modern Python packaging standard** (PEP 518) that replaces the old `setup.py` approach. It's a single configuration file that tells Python tools how to build, install, and manage your package.

## Why Use It?

### Before (Old Way):
- Required `setup.py` (Python code that was hard to maintain)
- Separate config files for different tools
- More complex and error-prone

### Now (Modern Way):
- Single `pyproject.toml` file (TOML format - easy to read/write)
- Standardized across Python ecosystem
- Works with modern tools (pip, setuptools, poetry, etc.)

## What Does Our pyproject.toml Do?

Let's break down each section:

### 1. Build System
```toml
[build-system]
requires = ["setuptools>=61.0", "wheel"]
build-backend = "setuptools.build_meta"
```
**What it does:** Tells pip/setuptools how to build your package into a distributable format (wheel).

### 2. Project Metadata
```toml
[project]
name = "mariadb-db-agents"
version = "0.1.0"
description = "AI-powered agents for MariaDB database management..."
```
**What it does:** Basic package information that appears on PyPI (if you publish it).

### 3. Dependencies
```toml
dependencies = [
    "openai-agents>=0.6.0",
    "mysql-connector-python>=9.0.0",
    "python-dotenv>=1.0.1",
]
```
**What it does:** Lists required packages. This is similar to `requirements.txt`, but it's the "official" way for packages.

**Note:** We still have `requirements.txt` for backward compatibility and simple `pip install -r requirements.txt` usage.

### 4. Optional Dependencies (Dev Tools)
```toml
[project.optional-dependencies]
dev = [
    "pytest>=7.0.0",
    "black>=23.0.0",
    "flake8>=6.0.0",
    "mypy>=1.0.0",
]
```
**What it does:** Development tools that aren't needed for end users. Install with: `pip install -e ".[dev]"`

### 5. Command-Line Scripts
```toml
[project.scripts]
mariadb-db-agents = "mariadb_db_agents.cli.main:main"
```
**What it does:** Creates a command-line script called `mariadb-db-agents` that runs the `main()` function from `mariadb_db_agents.cli.main`.

**After installation, users can run:**
```bash
mariadb-db-agents slow-query --hours 1
```
Instead of:
```bash
python -m mariadb_db_agents.cli.main slow-query --hours 1
```

### 6. Package Discovery
```toml
[tool.setuptools.packages.find]
where = ["."]
include = ["mariadb_db_agents*"]
exclude = ["tests*", "scripts*"]
```
**What it does:** Tells setuptools which directories to include in the package (include `mariadb_db_agents/` but exclude `tests/` and `scripts/`).

### 7. Tool Configuration
```toml
[tool.black]
line-length = 100

[tool.mypy]
python_version = "3.8"
```
**What it does:** Configuration for code formatting (black) and type checking (mypy) tools.

## How to Use It

### Install in Development Mode (Editable Install)
```bash
cd mariadb_db_agents
pip install -e .
```

**What this does:**
- Installs the package so Python can import it
- Links to your source code (changes are immediately available)
- Installs dependencies automatically
- Creates the `mariadb-db-agents` command

### Install Production Version
```bash
pip install .
```

**What this does:**
- Copies code to site-packages (not linked)
- Installs dependencies
- Creates the `mariadb-db-agents` command

### Install with Dev Dependencies
```bash
pip install -e ".[dev]"
```

**What this does:**
- Everything from `-e .` PLUS
- Installs pytest, black, flake8, mypy for development

### Build Distribution Package
```bash
pip install build
python -m build
```

**What this does:**
- Creates `dist/mariadb_db_agents-0.1.0.tar.gz` (source distribution)
- Creates `dist/mariadb_db_agents-0.1.0-py3-none-any.whl` (wheel)
- These can be uploaded to PyPI or shared directly

## pyproject.toml vs requirements.txt

| Feature | pyproject.toml | requirements.txt |
|---------|----------------|------------------|
| **Purpose** | Package metadata + dependencies | Simple dependency list |
| **Used by** | pip, setuptools, poetry, etc. | pip only |
| **Can create CLI commands** | ✅ Yes | ❌ No |
| **Can specify Python version** | ✅ Yes | ❌ No |
| **Can include metadata** | ✅ Yes | ❌ No |
| **Simple to use** | More features | Simpler |

**Best Practice:** Use both!
- `pyproject.toml` - For package installation and distribution
- `requirements.txt` - For simple `pip install -r requirements.txt` workflows

## Real-World Example

### Before pyproject.toml:
```bash
# User had to:
git clone repo
cd repo
pip install -r requirements.txt
python -m mariadb_db_agents.cli.main slow-query --hours 1
```

### With pyproject.toml:
```bash
# User can:
git clone repo
cd repo
pip install -e .
mariadb-db-agents slow-query --hours 1  # Cleaner command!
```

## Benefits for Your Project

1. **Professional Package Structure** - Standard Python packaging
2. **Easy Installation** - `pip install -e .` installs everything
3. **CLI Command** - Users get `mariadb-db-agents` command
4. **Future Publishing** - Ready to publish to PyPI if desired
5. **Tool Integration** - Works with modern Python tools
6. **Dependency Management** - Centralized dependency list

## Summary

`pyproject.toml` is like a "package.json" for Python - it defines:
- What your package is (name, version, description)
- What it needs (dependencies)
- How to install it (build system)
- What commands it provides (scripts)
- How tools should work (black, mypy config)

It makes your project more professional and easier for others to use!


