# Repository Structure Standards

This guideline defines the required structure for new Python repositories. These are not suggestions—they are requirements that ensure consistency and maintainability.

## Required Files

Every repository MUST contain:

```
project-root/
├── pyproject.toml          ← Project configuration (REQUIRED)
├── README.md               ← Project documentation (REQUIRED)
├── src/
│   └── package_name/       ← Source code (REQUIRED)
│       └── __init__.py
├── tests/                  ← Test files (REQUIRED)
│   └── __init__.py
└── .gitignore              ← Git ignores (REQUIRED)
```

## pyproject.toml Structure

### Build System

MUST use modern Python packaging:

```toml
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"
```

### Project Metadata

```toml
[project]
name = "your-project-name"
version = "0.1.0"
description = "Clear, concise description"
readme = "README.md"
requires-python = ">=3.11"
license = "MIT"
authors = [
    { name = "Your Name", email = "you@example.com" }
]
dependencies = []
```

### Dependency Organization

MUST separate dependencies by purpose:

```toml
[project.optional-dependencies]
# Development tools - ALWAYS in dev, never in main dependencies
dev = [
    "pytest>=8.0",
    "pytest-cov>=4.0",
    "ruff>=0.8",
]

# Optional heavy dependencies - let users choose variants
# Example: OpenCV has multiple distributions
opencv = ["opencv-python>=4.0.0"]
opencv-headless = ["opencv-python-headless>=4.0.0"]
opencv-contrib = ["opencv-contrib-python>=4.0.0"]
```

**Dependency Rules:**

- MUST NOT put pytest, ruff, or other dev tools in main `dependencies`
- MUST put testing tools in `dev` optional dependencies
- MUST offer variant optional dependencies for libraries with multiple distributions (OpenCV, PyTorch CPU/GPU)
- SHOULD pin minimum versions, not exact versions

### Ruff Configuration

MUST configure ruff with 120-character line length:

```toml
[tool.ruff]
line-length = 120
target-version = "py311"
src = ["src", "tests"]

[tool.ruff.lint]
select = [
    "E",      # pycodestyle errors
    "W",      # pycodestyle warnings
    "F",      # Pyflakes
    "I",      # isort
    "B",      # flake8-bugbear
    "C4",     # flake8-comprehensions
    "UP",     # pyupgrade
    "ARG",    # flake8-unused-arguments
    "SIM",    # flake8-simplify
]
ignore = [
    "E501",   # line too long (handled by formatter)
]

[tool.ruff.lint.isort]
known-first-party = ["your_package"]

[tool.ruff.format]
quote-style = "double"
indent-style = "space"
```

### Pytest and Coverage Configuration

```toml
[tool.pytest.ini_options]
testpaths = ["tests"]
pythonpath = ["src"]
addopts = [
    "-ra",
    "-q",
    "--strict-markers",
    "--cov=src",
    "--cov-report=term-missing",
    "--cov-branch",
]

[tool.coverage.run]
omit = [
    "*/__init__.py",    # Often empty imports
    "*/tests/*",        # Don't track coverage of the tests themselves
    "*/config.py",      # Configuration often hard to test
]

[tool.coverage.report]
fail_under = 80
show_missing = true
```

## Directory Conventions

### src/ Layout

MUST use the `src/` layout pattern:

```
src/
└── package_name/
    ├── __init__.py
    ├── core.py           ← Main functionality
    ├── utils.py          ← Helper functions
    └── py.typed          ← Marker for type hints
```

**Why src/ layout:**
- Prevents accidental imports of uninstalled package
- Ensures tests run against installed package
- Standard pattern recognized by tools

### tests/ Layout

MUST mirror the src/ structure:

```
tests/
├── __init__.py
├── test_core.py          ← Tests for core.py
├── test_utils.py         ← Tests for utils.py
└── conftest.py           ← Shared fixtures
```

### scraps/ Directory

SHOULD use `scraps/` for scratch work:

```
scraps/                   ← MUST be in .gitignore
├── experiments/          ← Quick experiments
├── notebooks/            ← Jupyter notebooks
└── debug/                ← Debug scripts
```

## .gitignore Requirements

MUST include at minimum:

```gitignore
# Python
__pycache__/
*.py[cod]
*.egg-info/
dist/
build/
.eggs/

# Virtual environments
.venv/
venv/
ENV/

# IDE
.idea/
.vscode/
*.swp

# Testing
.pytest_cache/
.coverage
htmlcov/

# RAE
scraps/
.rae-version

# OS
.DS_Store
Thumbs.db
```

## Red Flags (Violations)

These patterns indicate non-compliance:

| Violation | Problem |
|-----------|---------|
| `setup.py` without `pyproject.toml` | Legacy packaging |
| `requirements.txt` as primary deps | Use pyproject.toml |
| pytest in main dependencies | Belongs in dev extras |
| No src/ directory | Flat layout causes import issues |
| Line length != 120 in ruff config | Inconsistent formatting |
| Missing .gitignore | Untracked files in repo |

## Verification Checklist

Before considering a repo properly structured:

- [ ] pyproject.toml exists with all required sections
- [ ] src/ layout used for package code
- [ ] tests/ directory exists with at least one test
- [ ] ruff configured with line-length = 120
- [ ] pytest configured with coverage (fail_under = 80)
- [ ] Dev dependencies in optional-dependencies, not main
- [ ] .gitignore includes all standard patterns
- [ ] README.md describes the project
