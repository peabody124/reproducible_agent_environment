# Python Standards

## Formatting & Linting

- MUST run `ruff format <file>` on every Python file touched
- MUST run `ruff check <file>` before handing off work
- When in doubt: `ruff format . && ruff check .` at the repo root

## Type Hints

- MUST use type hints for function signatures
- Use `jaxtyping` for array shapes in numerical code
- MUST NOT use `Any` to bypass type checking
- MUST NOT add `# type: ignore` without explanation

## Path Management

- MUST NOT modify `sys.path` or use import hacks
- MUST NOT hardcode absolute paths (e.g., `/home/...`)
- Use the installed package layout and `pathlib` relative to the project root or configured data directories

## Project Layout

- Use `src/` layout for packages
- Tests in `tests/` mirroring src structure
- Scratch work in `scraps/` (gitignored)

## Dependencies

- Use `uv` for package management
- Pin versions in `pyproject.toml`
- Prefer well-maintained, actively developed libraries

## Error Handling

- Only validate at system boundaries (user input, external APIs)
- Trust internal code and framework guarantees
- Don't add error handling for scenarios that can't happen
