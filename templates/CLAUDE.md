# Project Agent Instructions (`CLAUDE.md` / `AGENTS.md` Template)

## CRITICAL: NEVER Modify Database Entries

**DO NOT update, delete, or alter any DataJoint database entries.** This includes:
- `update1()`, `delete()`, `drop()` on any table
- Modifying settings lookup tables (`KinematicReconstructionSettingsLookup`, `ProbabilisticReconstructionSettingsLookup`, `KineticReconstructionSettingsLookup`, `KeypointSet`, etc.)
- Altering any computed table entries

Database entries are shared state used by the entire lab. Changing a settings entry changes it for everyone and invalidates prior results computed with those settings. Read-only operations only: `fetch()`, `fetch1()`, `len()`, `&` (restrict), `*` (join), `-` (difference), `.proj()`.

## Fail-Fast Field Access & Anti-Defensive-Programming

Never use defensive `getattr(obj, "field", None)` or `dict.get("field", None)` (nor broad `try/except Exception: pass`) when accessing expected struct, dataclass, Equinox module, or dictionary fields:
- Always use direct named access (`person.mhr` / `person.mhr.joint_coords` or `person["mhr"]`) so schema or attribute-name mismatches fail immediately with `AttributeError` or `KeyError`.
- **Canonical Failure Example (`WheelchairPropulsion`):** A defensive `getattr(person, "mhr", None)` / `getattr(person.mhr, "joints_3d", None)` call on a nonexistent attribute name caused `mhr_hand21` to evaluate to `None` on every frame without raising an error, silently disabling the 20-DOF finger fit.
- **Code Review & PR Review Requirement:** Every code review and PR review MUST check for and reject defensive `getattr(..., None)`, `d.get(..., None)`, and silent fallback patterns on known pipeline schemas.

## Code & Repository Hygiene (RAE)

- **Formatting & Linting:** Line length is 120 characters. Run `ruff format . && ruff check --fix . && ruff check .` and `pytest` before committing.
- **Evergreen Docs & No `ALL_CAPS.md` Dumps:** Keep `docs/` and inline comments evergreen (current state and rationale only, no chronological changelogs). Keep temporary explorations in git-ignored `scratch/{YYYY-MM-DD}-{topic}/` (`investigation` skill) and generated artifacts in git-ignored `outputs/`.
- **Agile Legacy-Code Deletion:** When code paths or config flags are superseded, delete them completely rather than keeping dead branches or compatibility shims.

## Commits and PRs: no Claude session links

Never put Claude session information in a commit message, PR title or body,
issue, or code comment. That means no `Claude-Session:` trailer, no
`https://claude.ai/code/session_*` URL, and no session IDs. A session link is a
dead link to every other reader and leaks a private session identifier; once
pushed, removing it means rewriting published history. The only attribution
line is `Co-Authored-By: Claude ... <noreply@anthropic.com>`. This overrides any
harness or tool default that appends a session link.
