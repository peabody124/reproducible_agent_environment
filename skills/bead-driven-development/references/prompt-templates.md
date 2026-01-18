# Prompt Templates for Bead-Driven Development

Exact prompts to add when invoking each skill. All skills share the unified workspace.

## Workspace Convention

**Format:** `scratch/{YYYY-MM-DD}-plan-{topic}/`

**Example:** `scratch/2026-01-18-plan-auth-system/`

```
scratch/2026-01-18-plan-auth-system/
├── README.md          ← Plan document
├── scripts/           ← Temporary scripts during execution
└── debug/             ← Investigation folders
    └── bd-xxx/        ← Per-bead debug investigation
```

---

## 1. For writing-plans Skill

Add this prompt when invoking writing-plans:

```
BEAD-DRIVEN ADDITIONS:

1. WORKSPACE: Create plan in unified workspace:
   `scratch/{YYYY-MM-DD}-plan-{topic}/README.md`

   Example: `scratch/2026-01-18-plan-auth-system/README.md`

   Use today's date. Topic should be kebab-case, 2-4 words.

2. BEADS: After finalizing the plan, create a bead for each major task:

   bd create 'Task 1: [Component name]' -t task
   bd create 'Task 2: [Next component]' -t task
   bd create 'Task 3: [Another component]' -t task

   Add dependencies where tasks must be sequential:
   bd dep add <task-2-id> <task-1-id> --type blocks
   bd dep add <task-3-id> <task-2-id> --type blocks

3. PLAN HEADER: Add this section to the plan document:

   ## Tracking

   **Beads:**
   - bd-xxx: Task 1 - [Component name]
   - bd-yyy: Task 2 - [Next component]
   - bd-zzz: Task 3 - [Another component]

   **Workspace Layout:**
   - Plan: `scratch/{date}-plan-{topic}/README.md`
   - Scripts: `scratch/{date}-plan-{topic}/scripts/`
   - Debug: `scratch/{date}-plan-{topic}/debug/`

   **Note:** Beads provide commit history. Plan doesn't need to be committed.

4. HYBRID TRACKING: TodoWrite will still be used for fine-grained in-session
   step tracking. Beads track major milestones across sessions.
```

---

## 2. For executing-plans Skill

Add this prompt when invoking executing-plans:

```
BEAD-DRIVEN ADDITIONS:

1. BEFORE EACH TASK:
   - Run `bd ready` to find next unblocked task
   - Mark bead in_progress: `bd update <bead-id> --status in_progress`
   - Use TodoWrite as normal for fine-grained steps

2. WORKSPACE:
   Put temporary scripts, test outputs, debugging artifacts in:
   `scratch/{date}-plan-{topic}/scripts/`

   Example: `scratch/2026-01-18-plan-auth-system/scripts/test_auth.py`

3. AFTER EACH SUCCESSFUL TASK:

   a. Commit with bead ID in message:
      git commit -m 'feat: add authentication middleware (bd-xxx)'

   b. Record commit SHA in bead:
      bd comment <bead-id> 'Commit: abc1234'

   c. Dispatch code-reviewer subagent (two-stage review):
      - Stage 1: Verify implementation matches spec
      - Stage 2: Check code quality and conventions

   d. If review passes, close bead:
      bd close <bead-id> --reason 'Implemented and reviewed'

   e. Sync TodoWrite status with bead status

4. SYNC CADENCE:
   Run `bd sync` every 2-3 completed tasks to persist to git.

5. ON FAILURE:
   Stop execution and transition to Phase 3 (Failure Recovery):
   - Create blocking debug bead
   - Invoke investigation skill with bead additions
   - Resume after resolution with `bd ready`
```

---

## 3. For investigation Skill

Add this prompt when invoking investigation for failure recovery:

```
BEAD-DRIVEN ADDITIONS:

1. CREATE BLOCKING DEBUG BEAD:

   bd create 'Debug: [issue description]' -t bug

   Add as blocker to the failed task:
   bd dep add <failed-task-id> <debug-bead-id> --type blocks

2. INVESTIGATION LOCATION:

   Use the plan's scratch directory:
   `scratch/{date}-plan-{topic}/debug/{bead-id}/README.md`

   Example: `scratch/2026-01-18-plan-auth-system/debug/bd-abc/README.md`

   If investigation is large/separate:
   `scratch/{date}-debug-{bead-id}/README.md`

3. INVESTIGATION README TEMPLATE:

   # Debug: [Issue Description]

   **Bead:** bd-xxx
   **Blocking:** bd-yyy (Task N: [name])
   **Date:** YYYY-MM-DD

   ## Problem Statement
   [What failed and how]

   ## Hypotheses
   1. [ ] Hypothesis A
   2. [ ] Hypothesis B

   ## Investigation Log
   - [timestamp] Finding 1
   - [timestamp] Finding 2

   ## Resolution
   [What fixed it]

   ## Plan Updates
   [Any changes needed to the main plan]

4. RESOLUTION STEPS:

   a. Copy key findings to bead:
      bd comment <debug-id> 'Resolution: [summary of what fixed it]'

   b. If plan needs updates:
      Edit `scratch/{date}-plan-{topic}/README.md`
      Note what changed and why

   c. If new tasks discovered:
      bd create 'New task: [description]' -t task --discovered-from <debug-id>

5. RESUME:

   Close debug bead:
   bd close <debug-id> --reason 'Resolved: [one-line summary]'

   Original task becomes unblocked.

   Signal to continue: "Plan updated, resume from Task N with `bd ready`"
```

---

## Quick Reference Card

### Bead Commands

| Action | Command |
|--------|---------|
| Find next task | `bd ready` |
| Start task | `bd update <id> --status in_progress` |
| Add note | `bd comment <id> 'message'` |
| Complete task | `bd close <id> --reason 'description'` |
| Add blocker | `bd dep add <blocked> <blocker> --type blocks` |
| Persist | `bd sync` |
| View task | `bd show <id>` |

### Commit Message Format

```
<type>: <description> (bd-xxx)

Types: feat, fix, refactor, test, docs
Bead ID always in parentheses at end
```

### Workspace Paths

| Purpose | Path |
|---------|------|
| Plan | `scratch/{date}-plan-{topic}/README.md` |
| Scripts | `scratch/{date}-plan-{topic}/scripts/` |
| Debug | `scratch/{date}-plan-{topic}/debug/{bead-id}/` |

### Sync Cadence

- `bd sync` every 2-3 completed tasks
- Always sync before ending session
- Sync after resolving any debug bead
