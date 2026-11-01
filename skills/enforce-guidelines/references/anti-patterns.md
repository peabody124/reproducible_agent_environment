# Anti-Patterns ("Slop")

These patterns indicate AI-generated code that needs cleanup. Use the `/deslop` skill to identify and remove them.

## Excessive Comments

- Comments explaining obvious code (`# increment counter`, `# return the result`)
- Redundant docstrings that just restate the function name
- Section dividers or decorative comments adding no value
- Comments describing what code does rather than why

## Paranoid Error Handling & Silent Defensive Lookups

- **Defensive `getattr(obj, "field", None)` or `dict.get("field", None)` on known schemas:** Never use `getattr(..., None)` or `.get(..., None)` when accessing expected attributes or keys on pipeline structs, dataclasses, Equinox modules, or result dicts. Use direct access (`obj.field` or `d["field"]`) so typos or schema drift raise `AttributeError` or `KeyError` immediately.
  - *Canonical failure mode:* In `WheelchairPropulsion`, `getattr(person, "mhr", None)` / `getattr(person.mhr, "joints_3d", None)` referenced a nonexistent attribute name and silently evaluated `mhr_hand21` to `None` on every frame without raising an error, silently disabling the 20-DOF finger fit.
- Try/catch blocks around internal code that won't fail
- Catching generic `Exception` without specific reason
- Swallowing errors with `pass` or logging-only handlers
- Defensive checks for impossible states
- **Code Review Mandate:** Always grep/check diffs during code review and PR review for `getattr(..., None)`, `.get(`, and broad `try/except` blocks on internal data structures.

## Type Evasion

- `Any` type casts to bypass type checking
- `# type: ignore` without explanation
- Missing return type hints
- Overly broad type unions when specific types are known

## Placeholder Patterns

- TODOs without actionable context or ownership
- "Phase 1" / "New" / "Updated" comments
- Stub implementations left in place
- Commented-out code blocks

## Over-Engineering

- Abstractions for single-use code
- Factory patterns for simple instantiation
- Configuration for things that won't vary
- Premature optimization without profiling
- Feature flags for things that will never be toggled

## Unnecessary Verbosity

- Multiple statements where one suffices
- Excessive intermediate variables with obvious names
- Redundant validation of internal state
- Re-exporting types that aren't used externally

## Database Mutation

- Calling `update1()`, `delete()`, or `drop()` on any DataJoint table
- Modifying settings lookup tables (KinematicReconstructionSettingsLookup, ProbabilisticReconstructionSettingsLookup, KineticReconstructionSettingsLookup, KeypointSet, etc.)
- Altering computed table entries
- Using `insert()` on shared tables without explicit user authorization

**Rule:** Database entries are shared lab state. Mutations change results for everyone and invalidate prior computations. Read-only access only.

## Backwards-Compatibility Hacks

- Renaming unused variables to `_var`
- Adding `# removed` comments for deleted code
- Re-exporting deprecated interfaces
- Keeping dead code "just in case"

**Rule:** If something is unused, delete it completely.
