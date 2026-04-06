# Git Workflow

## Staging Discipline

- MUST NOT run `git add .` or `git add <dir>`
- Explicitly add only the files/sections that are part of the intentional change
- Review staged changes before commit to avoid shipping unrelated edits

## Commit Standards

- Atomic commits: one logical change per commit
- Clear commit messages describing "why" not just "what"
- No debug code, print statements, or scratch files in commits

## Formatting-Only Commits

When running `ruff format` or `ruff check --fix` triggers a large number of whitespace
or style changes across files, those formatting changes MUST be committed separately
from meaningful logic changes. This keeps diffs reviewable and `git blame` useful.

- Run formatting first, commit as `style: ruff format` or `style: apply ruff fixes`
- Then make your logic changes in a separate commit
- If only a few lines of formatting are interleaved with your changes, a single commit is fine

## Pre-Commit Checklist

Before every commit:
1. Run `ruff format` on changed files
2. Run `ruff check` and fix issues
3. Run `/deslop` to clean AI artifacts
4. Run `pytest` for any logic changes
5. Review staged files explicitly

## Scraps Directory

- Use `scraps/` for ad-hoc notebooks or throwaway scripts
- Create if needed, add to `.gitignore`
- MUST NOT include in commits

## Branch Hygiene

- Use descriptive branch names
- Keep branches focused on single features/fixes
- Delete branches after merging
