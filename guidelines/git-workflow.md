# Git Workflow

## Staging Discipline

- MUST NOT run `git add .` or `git add <dir>`
- Explicitly add only the files/sections that are part of the intentional change
- Review staged changes before commit to avoid shipping unrelated edits

## Commit Standards

- Atomic commits: one logical change per commit
- Clear commit messages describing "why" not just "what"
- No debug code, print statements, or scratch files in commits

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
