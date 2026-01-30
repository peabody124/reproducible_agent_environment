# Pre-Commit Checklist

## Overview

Workflow to run before committing any changes to ensure quality and consistency. This SOP should be followed for every commit.

## Trigger

Before running `git commit` on any changes.

## Steps

### 1. Run Formatters

**Constraints:**
- You MUST run `ruff format` on all changed Python files
- You MUST run `ruff check` and fix any issues before proceeding
- You SHOULD run `ruff check --fix` to auto-fix simple issues

**Commands:**
```bash
ruff format <changed-files>
ruff check <changed-files>
```

### 2. Run Deslop

**Constraints:**
- You MUST invoke the deslop skill on staged changes
- You MUST address any identified anti-patterns before committing
- You SHOULD prioritize MUST-fix items from anti-patterns.md

**Command:**
```
/deslop
```

### 3. Verify Tests

**Constraints:**
- You MUST run `pytest` for any logic changes
- You SHOULD add tests for new functionality (TDD mandate)
- You MUST NOT commit if tests fail
- You MAY skip tests for documentation-only changes

**Command:**
```bash
pytest
```

### 4. Review Staging

**Constraints:**
- You MUST review staged files explicitly
- You MUST NOT use `git add .` or `git add <directory>`
- You MUST NOT include debug code or scratch files
- You MUST verify no secrets or credentials are staged

**Commands:**
```bash
git status
git diff --staged
```

### 5. Commit

**Constraints:**
- You MUST write clear commit message explaining "why" not just "what"
- You SHOULD reference issues or context if applicable
- You MUST NOT include "WIP" or incomplete changes

**Format:**
```
<type>: <summary>

<body explaining why this change was made>

[optional: references to issues]
```

**Types:** feat, fix, refactor, docs, test, chore

## Quick Reference

```bash
# Full pre-commit workflow
ruff format .
ruff check . --fix
pytest
git status
# /deslop (in agent)
git add <specific-files>
git commit -m "type: summary"
```

## Troubleshooting

**Ruff check fails:** Run `ruff check --fix` first, then manually fix remaining issues.

**Tests fail:** Do not commit. Fix the issue or revert the breaking change.

**Forgot to run deslop:** Use `git commit --amend` after running deslop (only if not pushed).
