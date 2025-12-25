# Anti-Patterns ("Slop")

These patterns indicate AI-generated code that needs cleanup. Use the `/deslop` skill to identify and remove them.

## Excessive Comments

- Comments explaining obvious code (`# increment counter`, `# return the result`)
- Redundant docstrings that just restate the function name
- Section dividers or decorative comments adding no value
- Comments describing what code does rather than why

## Paranoid Error Handling

- Try/catch blocks around internal code that won't fail
- Catching generic `Exception` without specific reason
- Swallowing errors with `pass` or logging-only handlers
- Defensive checks for impossible states

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

## Backwards-Compatibility Hacks

- Renaming unused variables to `_var`
- Adding `# removed` comments for deleted code
- Re-exporting deprecated interfaces
- Keeping dead code "just in case"

**Rule:** If something is unused, delete it completely.
