# Python Standards

These are mandatory standards for Python development. Violations require correction before code is considered complete.

## Formatting & Linting

**Line length is 120 characters.** This is not negotiable.

- MUST run `ruff format <file>` on every Python file touched
- MUST run `ruff check --fix <file>` to auto-fix issues
- MUST run `ruff check <file>` before handing off work
- When in doubt: `ruff format . && ruff check --fix . && ruff check .`

**Ruff configuration** (in pyproject.toml):

```toml
[tool.ruff]
line-length = 120
target-version = "py311"
```

## Type Hints

- MUST use type hints for all function signatures
- MUST use type hints for class attributes
- Use `jaxtyping` for array shapes in numerical code
- MUST NOT use `Any` to bypass type checking
- MUST NOT add `# type: ignore` without inline explanation

**Good:**
```python
def process_data(items: list[str], threshold: float = 0.5) -> dict[str, int]:
    ...
```

**Bad:**
```python
def process_data(items, threshold=0.5):  # Missing type hints
    ...
```

## Path Management

- MUST NOT modify `sys.path` or use import hacks
- MUST NOT hardcode absolute paths (e.g., `/home/...`, `/Users/...`)
- Use `pathlib.Path` for all path operations
- Use `importlib.resources` for package data access
- Configure data directories via environment variables or config files

**Good:**
```python
from pathlib import Path
data_dir = Path(__file__).parent / "data"
```

**Bad:**
```python
import sys
sys.path.insert(0, "/home/user/myproject")  # Never do this
```

## Project Layout

MUST use the `src/` layout:

```
project/
├── src/
│   └── package_name/
│       ├── __init__.py
│       └── core.py
├── tests/
│   └── test_core.py
└── pyproject.toml
```

- Source code in `src/package_name/`
- Tests in `tests/` mirroring src structure
- Scratch work in `scraps/` (gitignored)

See `references/repo-structure.md` for complete requirements.

## Dependencies

- Use `uv` for package management
- Define dependencies in `pyproject.toml`, not requirements.txt
- Dev tools (pytest, ruff) go in `[project.optional-dependencies]` under `dev`
- Pin minimum versions: `"package>=1.0"` not `"package==1.0.0"`
- Prefer well-maintained, actively developed libraries

**Dependency location rules:**

| Dependency Type | Location |
|----------------|----------|
| Runtime required | `[project.dependencies]` |
| Testing (pytest, coverage) | `[project.optional-dependencies] dev` |
| Linting (ruff) | `[project.optional-dependencies] dev` |
| Optional features | `[project.optional-dependencies] feature-name` |

## Error Handling

- Only validate at system boundaries (user input, external APIs, file I/O)
- Trust internal code and framework guarantees
- Don't add error handling for scenarios that can't happen
- Don't catch generic `Exception` without re-raising or specific handling

**Good:**
```python
def load_config(path: Path) -> Config:
    if not path.exists():
        raise FileNotFoundError(f"Config not found: {path}")
    return Config.from_file(path)
```

**Bad:**
```python
def add_numbers(a: int, b: int) -> int:
    try:  # Unnecessary - internal code, can't fail
        return a + b
    except Exception:
        return 0
```

## Testing

- MUST write tests before or alongside implementation (TDD preferred)
- MUST run `pytest` before considering work complete
- MUST maintain ≥80% code coverage (enforced by pyproject.toml)
- Test files named `test_*.py`
- Test functions named `test_*`
- Use fixtures in `conftest.py` for shared setup

**Coverage configuration** (in pyproject.toml):

```toml
[tool.pytest.ini_options]
addopts = ["--cov=src", "--cov-report=term-missing", "--cov-branch"]

[tool.coverage.run]
omit = ["*/__init__.py", "*/tests/*", "*/config.py"]

[tool.coverage.report]
fail_under = 80
show_missing = true
```

See `references/coding-standards.md` for TDD requirements.

## Red Flags (Violations)

These patterns indicate non-compliance:

| Violation | Required Action |
|-----------|-----------------|
| `ruff check` shows errors | Fix all errors |
| Missing type hints | Add complete type annotations |
| `sys.path` modification | Remove and fix imports properly |
| Hardcoded paths | Use pathlib and config |
| pytest in main dependencies | Move to dev optional-dependencies |
| Line length != 120 | Update ruff config |
| Coverage < 80% | Add tests for uncovered code |
