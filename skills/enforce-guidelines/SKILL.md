---
name: enforce-guidelines
description: Mandatory skill that ensures all work follows RAE guidelines. Activates automatically before any code task.
---

## The Iron Law

**IF A GUIDELINE APPLIES TO YOUR TASK, YOU DO NOT HAVE A CHOICE. YOU MUST FOLLOW IT.**

This is not a suggestion. Guidelines are requirements. Violations require correction before work is considered complete.

## When This Skill Activates

This skill activates automatically when:

- Writing Python code → `python-standards.md`, `coding-standards.md`
- Creating a new repository → `repo-structure.md`
- Making commits → `git-workflow.md`
- Reviewing or refactoring code → `anti-patterns.md`
- Any code changes → `coding-standards.md`

**You MUST check for applicable guidelines before starting any task.** Even a 1% chance a guideline applies means you consult it.

## Decision Flow

Before responding to ANY code-related request:

```
1. What type of task is this?
   └─→ Identify: python, git, new-repo, refactor, debug, review

2. Which guidelines apply?
   └─→ Map task type to required guidelines (see mapping below)

3. Read the applicable guidelines
   └─→ Actually read them, don't assume you know the content

4. Extract MUST/MUST NOT constraints
   └─→ These are non-negotiable requirements

5. Proceed with task, citing guidelines when they influence decisions
```

## Where to Find Guidelines

Guidelines are bundled with the RAE plugin. Look for them in order of precedence:

1. **Project-local:** `./guidelines/*.md` (if vendored)
2. **Plugin bundle:** Bundled with RAE plugin installation
3. **RAE repository:** https://github.com/peabody124/reproducible_agent_environment/tree/main/guidelines

If you cannot find guidelines, check `.agent_setup_instructions/` for setup help.

## Guideline Mapping

| Task Type | Required Guidelines |
|-----------|-------------------|
| Any Python code | `python-standards.md`, `coding-standards.md` |
| New repository | `repo-structure.md`, `python-standards.md` |
| Git operations | `git-workflow.md` |
| Refactoring | `anti-patterns.md`, `coding-standards.md` |
| Code review | `anti-patterns.md`, `python-standards.md` |
| Bug fixes | `coding-standards.md` (TDD section) |
| New features | `coding-standards.md`, `python-standards.md` |

## Red Flags (Rationalization Detection)

These thoughts indicate you're trying to skip guidelines:

| Thought | Reality |
|---------|---------|
| "This is just a quick fix" | Quick fixes still follow guidelines |
| "I already know the standards" | Read them anyway, they may have changed |
| "This is too simple to need guidelines" | Simple code still needs type hints and formatting |
| "I'll fix it later" | Fix it now, there is no later |
| "The user didn't ask for TDD" | TDD is the default, not optional |
| "100 chars is close enough to 120" | Line length is 120, configure ruff correctly |

## Enforcement Mechanism

### Before Starting Work

1. **Identify task type** from the mapping above
2. **Read applicable guidelines** - actually open and read them
3. **Extract key constraints** - list the MUST/MUST NOT rules
4. **Acknowledge constraints** - state which rules apply to this task

### During Work

1. **Cite guidelines** when they influence a decision
2. **Check compliance** before completing each step
3. **Run verification commands** (ruff, pytest) as guidelines require

### Before Completing Work

1. **Run all required checks**: `ruff format . && ruff check . && pytest`
2. **Verify coverage**: pytest runs with `--cov` by default, coverage must be ≥80%
3. **Verify against checklist** from applicable guidelines
4. **Confirm no violations** remain

## Constraints

- You MUST read guidelines before starting code tasks
- You MUST cite the specific guideline when it influences a decision
- You MUST NOT skip guidelines because the task seems simple
- You MUST NOT proceed if guideline compliance is unclear
- You MUST run `ruff format` and `ruff check` before completing Python work
- You MUST run `pytest` if tests exist
- You SHOULD flag if you discover a case not covered by guidelines

## Verification Checklist

Before marking any code task complete:

- [ ] Identified applicable guidelines
- [ ] Read the guidelines (not just remembered them)
- [ ] Listed MUST constraints that apply
- [ ] Followed all MUST constraints
- [ ] Avoided all MUST NOT patterns
- [ ] Ran `ruff format` on changed files
- [ ] Ran `ruff check` with no errors
- [ ] Ran `pytest` with coverage ≥80%
- [ ] No anti-patterns from `anti-patterns.md`

**Cannot check all boxes? Work is not complete.**

## Examples

**User:** "Add a helper function to parse dates"

**Agent (correct):**
> This is Python code, so I need to consult `python-standards.md` and `coding-standards.md`.
>
> Key constraints:
> - MUST use type hints for function signatures
> - MUST run ruff format/check
> - SHOULD write test first (TDD)
>
> Let me write a failing test first, then implement...

**Agent (incorrect):**
> Sure, here's a quick function:
> ```python
> def parse_date(s):
>     return datetime.strptime(s, "%Y-%m-%d")
> ```

The incorrect response skips guidelines consultation, misses type hints, and doesn't run verification.
