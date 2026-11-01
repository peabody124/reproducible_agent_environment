# Coding Standards

## CRITICAL: NEVER Modify Database Entries

**DO NOT update, delete, or alter any DataJoint database entries.** This includes:
- `update1()`, `delete()`, `drop()` on any table
- Modifying settings lookup tables (KinematicReconstructionSettingsLookup, ProbabilisticReconstructionSettingsLookup, KineticReconstructionSettingsLookup, KeypointSet, etc.)
- Altering any computed table entries

Database entries are shared state used by the entire lab. Changing a settings entry changes it for everyone and invalidates prior results computed with those settings.

**Read-only operations only:** `fetch()`, `fetch1()`, `len()`, `&` (restrict), `*` (join), `-` (difference), `.proj()`.

## Test-Driven Development Mandate

**ALWAYS ISOLATE BUGS WITH A UNIT TEST BEFORE FIXING.**

1. Create a minimal reproduction script in `tests/` that fails under the current code
2. Implement the fix
3. Verify the fix by running the reproduction script and ensuring it passes
4. Commit the test to prevent regression

## Fail-Fast Field Access & Anti-Defensive-Programming

- **MUST NOT** use defensive `getattr(obj, "field", None)` or `dict.get("field", None)` (nor `dict.setdefault` or `hasattr` checks) when accessing expected struct, dataclass, Equinox module, or dictionary fields. Use direct named access (`person.mhr` / `person.mhr.joint_coords` or `data["mhr"]`) so schema or attribute-name mismatches fail immediately with `AttributeError` or `KeyError`.
- **Canonical Incident (`WheelchairPropulsion`):** A defensive `getattr(person, "mhr", None)` / `getattr(person.mhr, "joints_3d", None)` check on a nonexistent attribute name (`joints_3d` instead of `joint_coords`) caused `mhr_hand21` to silently evaluate to `None` on every frame without raising an error, silently disabling the 20-DOF finger fit across the entire run.
- **MUST NOT** swallow exceptions with broad `try / except Exception: pass` or warning-only handlers around internal pipeline stages, DataJoint queries, or checkpoint loads.
- **Code Review & PR Review Requirement:** Every code review and PR review MUST explicitly inspect the diff for `getattr(..., None)`, `.get(..., None)`, and broad `try/except` blocks on known schemas and reject them in favor of direct fail-fast access.

## DRY & Code Organization

- MUST search for existing helpers before writing new logic
- STRONGLY AVOID creating new files for small pieces of code
- Think hard about code organization; heavily consider if there is an existing location where new code would naturally go
- Refactor duplication into shared utilities immediately

## Configuration

- Prefer passing Pydantic models or config dictionaries intact rather than exploding them into dozens of individual parameters
- MUST NOT scatter constants (model names, thresholds, K-factors) throughout the code
- Constants belong in config files or dedicated modules

## Single Source of Truth

- MUST NOT hide defaults inside code
- All constants (thresholds, model names, magic numbers) in dedicated config
- Never duplicate configuration values across files

## Documentation

- Comments MUST be evergreen—describe current reality only
- MUST NOT add comments like "New", "Phase 1", "TODO: later", or development workflow notes
- No temporary plans in commits; keep scratch work under ignored paths
- Only add comments where the logic isn't self-evident
