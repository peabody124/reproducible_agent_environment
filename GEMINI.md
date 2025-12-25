# Agent Instructions

## User Context
- Name: James Cotton
- Role: Physician-Scientist
- Domains: Biomechanics, Rehabilitation, Motion Capture

## Guidelines

You MUST consult and follow these guidelines:

- `guidelines/coding-standards.md` — Core development practices (TDD, DRY, fail-fast)
- `guidelines/python-standards.md` — Python-specific rules (ruff, typing, paths)
- `guidelines/git-workflow.md` — Git discipline and commit standards
- `guidelines/anti-patterns.md` — What to avoid ("slop")

## Workflow

- Before starting work: Review relevant guidelines for the task type
- Before commits: Clean AI artifacts from code
- When discovering improvements: Propose upstream to this repository

## Conductor Integration

This project supports Gemini Conductor for context-driven development:
- Use `conductor setup` to initialize project context
- Use `conductor new track` to create specs and plans
- Use `conductor implement` to execute approved plans

## Tech Stack Preferences

- Python with `uv` for package management
- JAX/jaxtyping for numerical work
- pytest for testing
- Strict `src/` and `tests/` layout
- ruff for formatting and linting

## Skills (via gemini-cli-skillz)

Skills are available through the skillz extension:
- `deslop` — Clean AI-generated slop from staged changes
- `consult-guidelines` — Review relevant guidelines for current task
- `config-improvement` — Propose improvements to upstream RAE repo
