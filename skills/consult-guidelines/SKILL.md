---
name: consult-guidelines
description: >
  Review relevant coding guidelines before starting a task. Use when the user says
  "consult guidelines", "check standards", "what are the rules for", "review guidelines",
  or when starting Python, git, refactoring, debugging, or code review work. Also useful
  when asking "what line length", "how should I format", "what's the testing policy".
---

## Overview

Read and internalize the coding guidelines relevant to the current task. Guidelines are
bundled as reference files in the `enforce-guidelines` skill at
`enforce-guidelines/references/`.

## Parameters

- **task_type** (optional): "python", "git", "refactor", "debug", "review", or "all"

## Steps

### 1. Determine Relevant Guidelines

Based on task type, identify which guidelines to review from `enforce-guidelines/references/`:

| Task Type | Guidelines to Read |
|-----------|-------------------|
| `python` | `coding-standards.md`, `python-standards.md` |
| `git` | `git-workflow.md`, `pre-commit-checklist.md` |
| `refactor` | `coding-standards.md`, `anti-patterns.md` |
| `debug` | `coding-standards.md` (TDD section) |
| `review` | `anti-patterns.md`, `coding-standards.md` |
| `new-repo` | `repo-structure.md`, `python-standards.md` |
| `all` | All guidelines |

### 2. Summarize Key Points

Extract the 3-5 most relevant rules for the current task.

- You MUST highlight any MUST/MUST NOT constraints
- You SHOULD note any task-specific gotchas

### 3. Apply During Work

Keep these guidelines in mind while executing the task. Reference them when making decisions.

- You MUST cite the relevant guideline when it influences a decision
- You SHOULD flag if you discover a case not covered by guidelines

## Examples

**User:** "I'm about to refactor the auth module"
**Agent:** Reads coding-standards.md and anti-patterns.md, summarizes DRY principles and slop patterns to avoid, proceeds with refactor while citing guidelines.

**User:** "/consult-guidelines python"
**Agent:** Reviews coding-standards.md and python-standards.md, extracts key rules about ruff, type hints, and path management.
