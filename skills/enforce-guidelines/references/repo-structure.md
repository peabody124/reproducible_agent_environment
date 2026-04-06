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

The canonical pyproject.toml template lives at `templates/pyproject.toml` in the RAE plugin.
That file is the **single source of truth** for all tool configuration (ruff, pytest, coverage).
Use `/audit-repo` to check an existing repo against it.

Key requirements (see the template for exact config):

- **Build system:** hatchling
- **Python:** >=3.11
- **Dev dependencies:** pytest, pytest-cov, ruff MUST go in `[project.optional-dependencies] dev`, never in main `dependencies`
- **Ruff:** line-length = 120, target-version = py311, full lint rule set (E, W, F, I, B, C4, UP, ARG, SIM)
- **Pytest:** pythonpath = ["src"], coverage via --cov addopts
- **Coverage:** fail_under = 80

MUST NOT put dev tools in main dependencies. SHOULD pin minimum versions, not exact versions.
MUST offer variant optional dependencies for libraries with multiple distributions (OpenCV, PyTorch CPU/GPU).

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
