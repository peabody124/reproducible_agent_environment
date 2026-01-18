---
description: Execute plan with beads tracking
allowed-tools:
  - Read
  - Write
  - Edit
  - Grep
  - Glob
  - Bash(bd *)
  - Bash(git add *)
  - Bash(git commit *)
  - Bash(git status)
  - Bash(git diff *)
  - Bash(git push *)
  - Bash(git log *)
  - Bash(mkdir *)
  - Task
  - TodoWrite
  - Skill
---

Use the `rae:bead-driven-development` skill to orchestrate planning and execution with persistent beads tracking.

This command is for multi-task development workflows where you want:
- Persistent task tracking across sessions (via beads)
- Automatic skill orchestration (writing-plans, executing-plans, investigation)
- Two-stage code review integration
- Unified workspace organization in `scratch/{date}-plan-{topic}/`

**Prerequisites:** beads CLI installed (`bd`), beads plugin active, superpowers plugin active.
