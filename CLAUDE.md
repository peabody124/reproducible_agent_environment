# Agent Instructions

## User Context
- Name: James Cotton
- Role: Physician-Scientist
- Domains: Biomechanics, Rehabilitation, Motion Capture

## Guidelines

You MUST consult and follow these guidelines. This is not optional.

Guidelines are bundled in `skills/enforce-guidelines/references/`:

- `skills/enforce-guidelines/references/coding-standards.md` — Core development practices (TDD, DRY, fail-fast)
- `skills/enforce-guidelines/references/python-standards.md` — Python-specific rules (ruff 120 chars, typing, paths)
- `skills/enforce-guidelines/references/repo-structure.md` — Repository layout and pyproject.toml requirements
- `skills/enforce-guidelines/references/git-workflow.md` — Git discipline and commit standards
- `skills/enforce-guidelines/references/anti-patterns.md` — What to avoid ("slop")

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
- `/bead-driven-development` — Orchestrate planning + execution with beads tracking
- `/investigation` — Scaffold structured research in scratch/

### Domain-Specific
- `/datajoint-biomechanics-schema` — DataJoint pipeline schema reference
- `/pose-datajoint` — Python code patterns for DataJoint pose queries
- `/gait-metrics` — Gait analysis: walking segments, spatiotemporal metrics, GDI
- `/jax-config` — JAX/Equinox-compatible config setup with pytree registration and tyro CLI
- `/camera-model` — Camera projections, intrinsics/extrinsics, triangulation, mm/m unit conventions
- `/gait-lab-dataset` — Clinical gait lab schema, video-mocap sync, MMC-GaitLab trial matching

## Tech Stack Preferences

- Python with `uv` for package management
- JAX/jaxtyping for numerical work
- pytest for testing (in dev dependencies, not main)
- Strict `src/` and `tests/` layout
- ruff for formatting and linting (line-length = 120)
