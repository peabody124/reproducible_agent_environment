# Agent Instructions

## User Context
- Name: James Cotton
- Role: Physician-Scientist
- Domains: Biomechanics, Rehabilitation, Motion Capture

## Guidelines

You MUST consult and follow these guidelines. This is not optional.

- `guidelines/coding-standards.md` — Core development practices (TDD, DRY, fail-fast)
- `guidelines/python-standards.md` — Python-specific rules (ruff 120 chars, typing, paths)
- `guidelines/repo-structure.md` — Repository layout and pyproject.toml requirements
- `guidelines/git-workflow.md` — Git discipline and commit standards
- `guidelines/anti-patterns.md` — What to avoid ("slop")

**Before any code task:** Consult applicable guidelines. See `/enforce-guidelines` for the required process.

## Workflow

1. Before starting work: Run `/enforce-guidelines` to identify applicable standards
2. During work: Cite guidelines when they influence decisions
3. Before commits: Run `/deslop` to clean AI artifacts
4. After completion: Verify with `ruff format . && ruff check . && pytest`

## Available Skills

### Mandatory (Auto-Activate)
- `/enforce-guidelines` — Ensures all work follows RAE guidelines. Activates automatically.

### Utility
- `/deslop` — Clean AI-generated slop from staged changes
- `/consult-guidelines` — Review relevant guidelines for current task
- `/scaffold-repo` — Initialize a new repository with correct structure
- `/config-improvement` — Propose improvements to upstream RAE repo

## Tech Stack Preferences

- Python with `uv` for package management
- JAX/jaxtyping for numerical work
- pytest for testing (in dev dependencies, not main)
- Strict `src/` and `tests/` layout
- ruff for formatting and linting (line-length = 120)
