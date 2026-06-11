# Agent Instructions

## User Context
- Name: James Cotton
- Role: Physician-Scientist
- Domains: Biomechanics, Rehabilitation, Motion Capture

## Guidelines

You MUST consult and follow the guidelines in `skills/enforce-guidelines/references/`.
The `/enforce-guidelines` skill activates automatically before code tasks.

The **single source of truth** for tool configuration (ruff, pytest, coverage) is
`templates/pyproject.toml`. Use `/audit-repo` to check if a repo has drifted from it.

## Workflow

1. During work: Follow guidelines in `skills/enforce-guidelines/references/`
2. Before commits: Run `/deslop` to clean AI artifacts
3. After completion: Verify with `ruff format . && ruff check . && pytest`

## Available Skills

### Mandatory (Auto-Activate)
- `/enforce-guidelines` — Ensures all work follows RAE guidelines. Activates automatically.

### Utility
- `/deslop` — Clean AI-generated slop from staged changes
- `/consult-guidelines` — Review relevant guidelines for current task
- `/scaffold-repo` — Initialize a new repository with correct structure
- `/audit-repo` — Check current repo against RAE standards, report drift, fix gaps
- `/config-improvement` — Propose improvements to upstream RAE repo
- `/bead-driven-development` — Orchestrate planning + execution with beads tracking (optional, disabled by default)
- `/investigation` — Scaffold structured research in scratch/
- `/excalidraw` — Generate Excalidraw diagrams, render to PNG/SVG, visually verify
- `/semi-formal-code-reasoning` — Structured reasoning templates for patch equivalence, fault localization, code QA, and code review
- `/github-activity-review` — Periodic cross-repo GitHub activity review with thematic organization

### Domain-Specific
- `/datajoint-biomechanics-schema` — DataJoint pipeline schema reference
- `/pose-datajoint` — Python code patterns for DataJoint pose queries
- `/fetching-synchronized-data` — Temporal alignment of keypoints with kinematic reconstruction
- `/gait-metrics` — Gait analysis: walking segments, spatiotemporal metrics, GDI
- `/jax-config` — JAX/Equinox-compatible config setup with pytree registration and tyro CLI
- `/jax-memory-and-retracing` — Diagnose/avoid GPU & host OOMs, memory leaks, and JIT retracing in JAX/Equinox
- `/camera-model` — Camera projections, intrinsics/extrinsics, triangulation, mm/m unit conventions
- `/efficient-rendering` — Fast, correct rendering of meshes/point clouds/overlays: EGL headless GPU, OpenCV↔GL conventions, distortion strategies, chunked JAX rasterizers, video compositing
- `/gait-lab-dataset` — Clinical gait lab schema, video-mocap sync, MMC-GaitLab trial matching

## CRITICAL: NEVER Modify Database Entries

See `skills/enforce-guidelines/references/coding-standards.md` for the full rule.
In short: **DO NOT** call `update1()`, `delete()`, `drop()` on any DataJoint table.
Database entries are shared lab state.
