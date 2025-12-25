# Tech Stack

## Language & Runtime

- **Python 3.11+** — Primary language
- **uv** — Package management
- **pytest** — Testing framework

## Key Libraries

<!-- Customize for your project -->

- **JAX** — Numerical computing and autodiff
- **jaxtyping** — Array shape annotations
- **Pydantic** — Data validation and settings

## Code Quality

- **ruff** — Formatting and linting (replaces black, isort, flake8)
- **mypy** — Static type checking (optional)

## Project Structure

```
project/
├── src/              # Source packages
│   └── package/
├── tests/            # Test files
├── scraps/           # Throwaway scripts (gitignored)
├── conductor/        # Conductor context
└── guidelines/       # RAE guidelines (synced)
```

## Constraints

- Must run on consumer GPU (if applicable)
- Prefer functional style for data transformations
- Classes for stateful components only
- No modification of sys.path

## Development Tools

- VS Code with Python extension
- Claude Code CLI for AI assistance
- Gemini CLI with Conductor for planning
