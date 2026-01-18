---
name: bead-driven-development
description: >
  Use when the user asks to "execute plan with beads", "implement with persistent tracking",
  "bead-driven execution", "run plan with subagents", or wants planning + subagents + beads +
  code review unified. Orchestrates writing-plans, executing-plans, and investigation skills
  with beads integration for persistent cross-session tracking.
---

# Bead-Driven Development

## Overview

This skill orchestrates existing skills with beads integration. It provides prompt refinements rather than reimplementing functionality:
- **writing-plans** → create plan + beads for major tasks
- **executing-plans** → use subagents + track via beads
- **investigation** → create blocking beads on failure, update plan

**Announce at start:** "I'm using the bead-driven-development skill to orchestrate planning and execution with persistent tracking."

## Prerequisites

This skill requires beads and superpowers plugins. Install them first:

### Install beads
```bash
# Install beads CLI
curl -fsSL https://raw.githubusercontent.com/steveyegge/beads/main/scripts/install.sh | bash

# Install uv (Python package manager)
curl -LsSf https://astral.sh/uv/install.sh | sh

# Add beads marketplace and install plugin
/plugin marketplace add steveyegge/beads
/plugin install beads
```

### Install superpowers
```bash
/plugin marketplace add obra/superpowers-marketplace
/plugin install superpowers@superpowers-marketplace
```

### Initialize beads in your repo
```bash
bd init
```

**Required skills from superpowers:**
- writing-plans
- executing-plans
- investigation (or from ~/.claude/skills/)

## Unified Workspace Convention

**All phases share one workspace:** `scratch/{YYYY-MM-DD}-plan-{topic}/`

```
scratch/2026-01-18-plan-auth-system/
├── README.md          ← Plan (Phase 1)
├── scripts/           ← Temp scripts (Phase 2)
└── debug/             ← Investigations (Phase 3)
    └── bd-xxx/
```

Beads provide the commit history. Plan doesn't need to be committed separately.

## Phase 1: Planning with Beads

Invoke **writing-plans** skill with these additions:

> "Create plan in unified workspace following investigation pattern:
> `scratch/{YYYY-MM-DD}-plan-{topic}/README.md`
> Example: `scratch/2026-01-18-plan-auth-system/README.md`
>
> After finalizing the plan, create a bead for each major task:
> ```bash
> bd create 'Task 1: Component name' -t task
> bd create 'Task 2: Next component' -t task
> bd dep add <task-2-id> <task-1-id> --type blocks
> ```
>
> Include bead IDs in the plan file for tracking.
>
> **Important**: Add a section in the plan noting:
> - Temp scripts go in: `scratch/{date}-plan-{topic}/scripts/`
> - Debug investigations go in: `scratch/{date}-plan-{topic}/debug/`
> - Beads provide commit history (plan doesn't need to be committed)
>
> Note: TodoWrite will still be used for fine-grained in-session tracking."

## Phase 2: Execution with Beads

Invoke **executing-plans** skill with these additions:

> "Before starting each task:
> 1. Run `bd ready` to find next unblocked task
> 2. Mark bead in_progress: `bd update <id> --status in_progress`
>
> Use TodoWrite as normal for fine-grained step tracking within the task.
>
> **Workspace**: Put any temporary scripts, test outputs, or debugging artifacts
> in the plan's scratch directory: `scratch/{date}-plan-{topic}/scripts/`
>
> After each successful task:
> 1. Commit with bead ID: `git commit -m 'feat: description (bd-xxx)'`
> 2. Add commit SHA to bead: `bd comment <id> 'Commit: <sha>'`
> 3. Dispatch code-reviewer subagent (per subagent-driven-development two-stage review)
> 4. If review passes: `bd close <id> --reason 'Implemented and reviewed'`
> 5. Sync TodoWrite → bead status when marking task complete
>
> Run `bd sync` every 2-3 completed tasks to persist to git.
>
> **On failure** → transition to Phase 3 (Failure Recovery)."

## Phase 3: Failure Recovery with Beads

When any task fails, invoke **investigation** skill with these additions:

> **Step 1: Create blocking debug bead**
> ```bash
> bd create 'Debug: <issue description>' -t bug
> bd dep add <failed-task-id> <debug-bead-id> --type blocks
> ```
>
> **Step 2: Investigation in plan's scratch directory**
> Create investigation subfolder:
> `scratch/{date}-plan-{topic}/debug/{bead-id}/README.md`
>
> Or if separate investigation needed:
> `scratch/{date}-debug-{bead-id}/README.md`
>
> Document findings, hypotheses, and tests in the investigation folder.
>
> **Step 3: Resolution**
> Copy key findings summary to debug bead:
> ```bash
> bd comment <debug-id> 'Resolution: <summary of fix>'
> ```
>
> If plan needs updates: edit `scratch/{date}-plan-{topic}/README.md` and note changes.
>
> If new tasks discovered:
> ```bash
> bd create 'New task from investigation' -t task --discovered-from <debug-id>
> ```
>
> **Step 4: Resume**
> Close debug bead:
> ```bash
> bd close <debug-id> --reason 'Resolved: <summary>'
> ```
>
> Original task becomes unblocked.
> Signal: "Plan updated, resume from Task N with `bd ready`"

## Hybrid Tracking Model

| Tool | Purpose | Scope |
|------|---------|-------|
| Beads | Major milestones/tasks | Cross-session persistence |
| TodoWrite | Fine-grained steps | In-session tracking |

**Sync rule**: When TodoWrite marks task complete → close corresponding bead.

## Quick Reference

| Command | Purpose |
|---------|---------|
| `bd ready` | Find next unblocked task |
| `bd update <id> --status in_progress` | Mark task started |
| `bd close <id> --reason '...'` | Mark task complete |
| `bd comment <id> 'message'` | Add context to bead |
| `bd dep add <id> <blocker> --type blocks` | Add dependency |
| `bd sync` | Persist to git (every 2-3 tasks) |
| `bd show <id>` | Get task context |

## Workflow Summary

```
User: "execute this plan with beads"
           ↓
[bead-driven-development loads]
           ↓
Phase 1: Invoke writing-plans + beads prompt
  → Creates unified workspace
  → Plan in README.md
  → Creates beads for major tasks
  → Adds blocks dependencies
           ↓
Phase 2: Invoke executing-plans + beads prompt
  → Uses bd ready to pick next task
  → Updates bead status + TodoWrite
  → Commits with bead ID: (bd-xxx)
  → Two-stage code review
  → Close bead after review
  → bd sync every 2-3 tasks
           ↓
(On failure) Phase 3: Invoke investigation + beads prompt
  → Creates blocking debug bead
  → Investigates in workspace: debug/{bead-id}/
  → Copies findings to bead notes
  → Updates README.md when resolved
  → Resumes with bd ready
```

## See Also

- `references/prompt-templates.md` - Exact copy-paste prompts for each skill
