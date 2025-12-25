# Coding Standards

## Test-Driven Development Mandate

**ALWAYS ISOLATE BUGS WITH A UNIT TEST BEFORE FIXING.**

1. Create a minimal reproduction script in `tests/` that fails under the current code
2. Implement the fix
3. Verify the fix by running the reproduction script and ensuring it passes
4. Commit the test to prevent regression

## Fail Fast

- MUST NOT hide missing data behind defaults (`dict.get`, `dict.setdefault`, `key in dict else`)
- MUST NOT use warning-only handlers for errors
- Let crashes surface real issues, especially regarding state management or validation errors

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
