# Pre-Commit Checklist

Quick reference for the commit workflow. See `git-workflow.md` for full rules.

```bash
# 1. Format (if large whitespace changes, commit separately first)
ruff format <changed-files>
ruff check --fix <changed-files>
ruff check <changed-files>

# 2. Clean AI artifacts
/deslop

# 3. Test (skip for docs-only changes)
pytest

# 4. Stage explicitly (NEVER git add . or git add <dir>)
git status
git diff --staged
git add <specific-files>

# 5. Commit
git commit -m "type: summary of why"
```

**Commit types:** feat, fix, refactor, docs, test, chore

**If formatting triggers many whitespace changes:** commit those separately as
`style: ruff format` before your logic changes. See `git-workflow.md`.
