---
name: deslop
description: Clean AI-generated slop from staged changes before commit
---

## Overview

Review staged changes (or specified scope) and remove common AI coding artifacts that reduce code quality. Reference `guidelines/anti-patterns.md` for the full list of patterns to identify.

## Parameters

- **scope** (optional, default: "staged"): "staged", "diff", or "file:<path>"

## Steps

### 1. Identify Slop Patterns

Scan the specified scope for these anti-patterns:

**Constraints:**
- You MUST flag excessive inline comments explaining obvious code
- You MUST flag paranoid try/catch blocks around internal code
- You MUST flag `Any` type casts that bypass type checking
- You MUST flag backwards-compatibility hacks (renamed `_vars`, `# removed` comments)
- You SHOULD flag placeholder TODOs without actionable context
- You SHOULD flag over-abstraction for single-use patterns
- You SHOULD flag unnecessary intermediate variables
- You MUST NOT remove comments that explain non-obvious business logic
- You MUST NOT remove error handling at system boundaries

### 2. Present Findings

List each instance with:
- File path and line number
- Category of slop (from anti-patterns.md)
- The problematic code snippet
- Suggested fix

**Constraints:**
- You MUST group findings by file
- You SHOULD prioritize MUST-fix items over SHOULD-fix items

### 3. Apply Fixes

Remove or simplify identified slop with user confirmation.

**Constraints:**
- You MUST preserve functional code behavior
- You MUST run `ruff format` after changes
- You MUST run `ruff check` to verify no new issues introduced
- You SHOULD batch related fixes together

## Examples

**User:** "/deslop"
**Agent:** Reviews staged changes, identifies 3 excessive comments and 1 unnecessary try/catch, offers to clean them.

**User:** "/deslop file:src/auth.py"
**Agent:** Scans auth.py specifically, finds 2 `Any` casts and 1 over-engineered factory pattern, proposes simplifications.
