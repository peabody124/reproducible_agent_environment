# Verify RAE Installation

Run these checks to confirm RAE is properly installed and working.

## Quick Verification

Run `/help` and confirm you see these RAE skills:
- `enforce-guidelines`
- `deslop`
- `scaffold-repo`
- `consult-guidelines`
- `config-improvement`

## Detailed Verification

### 1. Plugin Status

```
/plugin list
```

Expected output includes:
```
rae@reproducible_agent_environment (installed)
```

### 2. Skill Activation Test

Try invoking a skill:

```
/consult-guidelines python
```

Should output guidance from `python-standards.md`.

### 3. Guidelines Access

The enforce-guidelines skill should be able to read:
- `guidelines/coding-standards.md`
- `guidelines/python-standards.md`
- `guidelines/repo-structure.md`

If these are not found locally, they should be accessible from the plugin bundle.

### 4. pyright-lsp Plugin

Verify the pyright-lsp plugin is installed:

```
/plugin list
```

Expected output includes:
```
pyright-lsp (installed)
```

Test that pyright works:

```bash
pyright --version
```

## Success Criteria

Installation is verified when:

1. ✓ RAE plugin shows as installed
2. ✓ pyright-lsp plugin shows as installed
3. ✓ All 5 RAE skills are available
4. ✓ `/consult-guidelines` returns guidance
5. ✓ `/enforce-guidelines` activates on code tasks

## If Verification Fails

See `troubleshooting.md` for common issues and solutions.
