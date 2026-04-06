---
name: audit-repo
description: >
  Audit the current repository against RAE standards. Use when the user says "audit repo",
  "check repo standards", "sync with RAE", "check for drift", "compare against template",
  or when you want to verify a repo follows RAE conventions. Compares pyproject.toml,
  CLAUDE.md, ruff config, pytest/coverage config, and dev dependencies against the
  canonical RAE template.
---

## Overview

Compare the current repository's configuration against the canonical RAE template
(`templates/pyproject.toml`) and report discrepancies. For major structural differences
(e.g., no `src/` layout in an established repo), ask the user before proposing changes.

**This skill does NOT automatically fix everything.** It reports what it finds, fixes
trivial gaps (missing ruff subsections, missing dev deps), and asks about anything
that would be disruptive to change.

## Steps

### 1. Read the Canonical Template

Read `templates/pyproject.toml` from the RAE plugin directory to get the current
source of truth. This template defines the expected configuration for:
- Build system (hatchling)
- Python version constraint (>=3.11)
- Dev dependencies (pytest, pytest-cov, ruff)
- Ruff config (line-length, lint rules, isort, format)
- Pytest config (testpaths, pythonpath, addopts, coverage)
- Coverage config (fail_under = 80)

### 2. Read the Current Repo

Read the current repository's:
- `pyproject.toml` (required — if missing, this is a scaffold-repo situation, not an audit)
- `CLAUDE.md` (optional but recommended)
- Directory structure (src/ vs flat layout)

### 3. Compare and Categorize

Compare each section and categorize discrepancies:

**Auto-fixable (apply without asking):**
- Missing `[tool.ruff.lint.isort]` section
- Missing `[tool.ruff.format]` section
- Missing `[tool.ruff]` `src` key
- Missing ruff lint rules that are in the template
- Missing `[tool.pytest.ini_options]` section
- Missing `[tool.coverage.run]` or `[tool.coverage.report]` sections

**Ask the user first:**
- No `src/` layout (established repos may have good reasons)
- Dev dependencies missing from `[project.optional-dependencies]` when they're
  installed some other way (e.g., devcontainer, system-level)
- `line-length` differs from 120
- Extra `ignore` rules not in the template (may be project-specific, e.g., F722 for jaxtyping)
- Missing CLAUDE.md (offer to create one)
- Build system differs from hatchling

**Informational only (report but don't change):**
- No `.github/` CI workflows
- No `.pre-commit-config.yaml` (RAE does not require this)
- Coverage threshold differs from 80 (may be intentionally lower for legacy repos)

### 4. Report Findings

Present a summary table:

```
## Audit Results: {repo_name}

### Aligned with RAE
- [x] ruff line-length = 120
- [x] Python >= 3.11
- ...

### Gaps Found
| Gap | Category | Action |
|-----|----------|--------|
| Missing [tool.ruff.format] | Auto-fix | Will add |
| Missing pytest config | Auto-fix | Will add |
| No src/ layout | Ask user | Uses body_models/ directly |
| Extra ignore F722 | Informational | Needed for jaxtyping |

### Recommended additions to CLAUDE.md
- Document F722 exception and why it's needed
- ...
```

### 5. Apply Fixes

- Apply all auto-fixable changes to `pyproject.toml`
- For each "ask user" item, present the discrepancy and ask whether to fix or document as intentional
- Intentional deviations should be noted in the repo's CLAUDE.md under a `## RAE Deviations` section so future audits understand why

### 6. Verify

After applying fixes:
```bash
ruff format --check .
ruff check .
```

Report any issues from the verification step.

## Important Notes

- The canonical source of truth is always `templates/pyproject.toml` in the RAE plugin
- This skill does NOT enforce `src/` layout changes on established repos — that's too disruptive
- Extra `ignore` rules are often legitimate (F722 for jaxtyping, etc.) — ask, don't remove
- The goal is convergence over time, not instant compliance
