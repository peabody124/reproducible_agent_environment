---
name: scaffold-repo
description: Initialize a new Python repository with correct structure following RAE guidelines
---

## Overview

This skill creates a properly structured Python repository from scratch. It enforces `guidelines/repo-structure.md` requirements automatically.

**Use when:**
- Creating a new Python project
- Converting an unstructured project to proper layout
- User says "new repo", "new project", "initialize", "scaffold"

## Parameters

- **name** (required): Project name (lowercase, hyphens allowed)
- **description** (required): One-line project description
- **package_name** (optional): Python package name (defaults to name with underscores)
- **author** (optional): Author name (defaults to "James Cotton")
- **extras** (optional): Additional optional-dependencies groups to include

## Steps

### 1. Validate Inputs

**Constraints:**
- You MUST verify project name is lowercase with hyphens only
- You MUST derive package_name from project name (replace hyphens with underscores)
- You MUST NOT proceed without a description

### 2. Create Directory Structure

Create the required structure:

```bash
mkdir -p src/{package_name}
mkdir -p tests
touch src/{package_name}/__init__.py
touch src/{package_name}/py.typed
touch tests/__init__.py
```

**Constraints:**
- You MUST use src/ layout
- You MUST create both src/ and tests/ directories
- You MUST include py.typed marker for type hint support

### 3. Create pyproject.toml

Generate pyproject.toml following `guidelines/repo-structure.md`:

```toml
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project]
name = "{name}"
version = "0.1.0"
description = "{description}"
readme = "README.md"
requires-python = ">=3.11"
license = "MIT"
authors = [
    { name = "{author}", email = "your@email.com" }
]
dependencies = []

[project.optional-dependencies]
dev = [
    "pytest>=8.0",
    "pytest-cov>=4.0",
    "ruff>=0.8",
]

[tool.hatch.build.targets.wheel]
packages = ["src/{package_name}"]

[tool.pytest.ini_options]
testpaths = ["tests"]
pythonpath = ["src"]
addopts = ["-ra", "-q", "--strict-markers", "--cov=src", "--cov-report=term-missing", "--cov-branch"]

[tool.coverage.run]
omit = ["*/__init__.py", "*/tests/*", "*/config.py"]

[tool.coverage.report]
fail_under = 80
show_missing = true

[tool.ruff]
line-length = 120
target-version = "py311"
src = ["src", "tests"]

[tool.ruff.lint]
select = ["E", "W", "F", "I", "B", "C4", "UP", "ARG", "SIM"]
ignore = ["E501"]

[tool.ruff.lint.isort]
known-first-party = ["{package_name}"]

[tool.ruff.format]
quote-style = "double"
indent-style = "space"
```

**Constraints:**
- You MUST set line-length = 120
- You MUST put pytest and ruff in dev optional-dependencies
- You MUST NOT put dev tools in main dependencies

### 4. Create .gitignore

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
scratch/
.rae-version

# OS
.DS_Store
Thumbs.db
```

### 5. Create README.md

```markdown
# {name}

{description}

## Installation

```bash
uv pip install -e ".[dev]"
```

## Development

```bash
# Run tests
pytest

# Format code
ruff format .

# Lint code
ruff check .
```

## License

MIT
```

### 6. Create Initial Test Files

Create `tests/conftest.py`:

```python
"""Shared test fixtures."""
```

Create `tests/test_placeholder.py`:

```python
"""Placeholder test to verify pytest works."""


def test_placeholder() -> None:
    """Remove this test once real tests exist."""
    assert True
```

**Constraints:**
- You MUST include type hints (-> None)
- You MUST include a docstring
- You MUST create conftest.py for shared fixtures
- This ensures pytest runs successfully from the start

### 7. Initialize Git (if not already)

```bash
git init
git add .
git commit -m "feat: Initialize {name} with RAE structure"
```

**Constraints:**
- You MUST NOT commit if already in a git repo with uncommitted changes
- You SHOULD offer to commit but confirm with user first

### 8. Verify Structure

Run verification:

```bash
ruff format .
ruff check .
pytest
```

**Constraints:**
- You MUST run ruff format before completing
- You MUST run ruff check with no errors
- You MUST run pytest with all tests passing

### 9. (Optional) Add Devcontainer

If the user wants devcontainer support, create `.devcontainer/` matching the RAE reference configuration:

- Copy the `Dockerfile` and `devcontainer.json` from the RAE repo's `.devcontainer/` directory
- This gives the project Python 3.11, ripgrep, Claude Code, pyright, and automatic RAE plugin installation

See the [RAE README](https://github.com/peabody124/reproducible_agent_environment#devcontainers) for details.

### 10. RAE Plugin Setup

Remind the user to install the RAE plugin and recommended plugins if not already configured:

```
/plugin marketplace add peabody124/reproducible_agent_environment
/plugin install rae@reproducible_agent_environment
```

Or run the full install script which also installs pyright-lsp, official Claude plugins (code-review, feature-dev, code-simplifier, plugin-dev), beads, and superpowers:

```bash
curl -fsSL https://raw.githubusercontent.com/peabody124/reproducible_agent_environment/main/scripts/install-user.sh | bash
```

## Adding Optional Dependencies

If user requests specific libraries, add appropriate optional-dependencies:

**OpenCV:**
```toml
[project.optional-dependencies]
opencv = ["opencv-python>=4.0.0"]
opencv-headless = ["opencv-python-headless>=4.0.0"]
opencv-contrib = ["opencv-contrib-python>=4.0.0"]
```

**PyTorch:**
```toml
[project.optional-dependencies]
torch-cpu = ["torch>=2.0"]
torch-cuda = ["torch>=2.0"]  # User installs with CUDA separately
```

**Jupyter:**
```toml
[project.optional-dependencies]
notebooks = ["jupyter>=1.0", "ipykernel>=6.0"]
```

## Examples

**User:** "/scaffold-repo my-analysis-tool A tool for analyzing motion capture data"

**Agent:**
1. Creates directory structure
2. Generates pyproject.toml with name="my-analysis-tool", package="my_analysis_tool"
3. Creates .gitignore, README.md
4. Creates placeholder test
5. Runs ruff format, ruff check, pytest
6. Reports success with next steps

**User:** "/scaffold-repo cv-processor Image processing pipeline --extras opencv-headless"

**Agent:**
1. Creates standard structure
2. Adds opencv-headless to optional-dependencies
3. Completes verification
