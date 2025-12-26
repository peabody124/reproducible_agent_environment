# RAE Agent Setup Checklist

Follow this checklist to ensure you're properly configured for RAE development.

## Prerequisites

You need Claude Code CLI installed. If running in a dev container, this should already be available.

## Step 1: Check if RAE Plugin is Installed

Run this command to check installed plugins:

```
/plugin list
```

Look for `rae@reproducible_agent_environment` in the output.

## Step 2: Install RAE Plugin (if not installed)

If RAE is not installed, run these commands:

```
/plugin marketplace add peabody124/reproducible_agent_environment
/plugin install rae@reproducible_agent_environment
```

## Step 3: Verify Skills are Available

After installation, these skills should be available:

| Skill | Purpose |
|-------|---------|
| `/enforce-guidelines` | Ensures work follows RAE standards (auto-activates) |
| `/deslop` | Remove AI-generated slop from code changes |
| `/scaffold-repo` | Create new repos with correct structure |
| `/consult-guidelines` | Review applicable guidelines |
| `/config-improvement` | Propose improvements to RAE |

Test by running `/help` and checking skills are listed.

## Step 4: Verify Guidelines Access

RAE guidelines should be accessible via the plugin. Key guidelines:

- `coding-standards.md` — TDD, DRY, fail-fast
- `python-standards.md` — ruff (120 chars), typing, paths
- `repo-structure.md` — pyproject.toml, src/ layout
- `git-workflow.md` — Commit standards
- `anti-patterns.md` — Slop patterns to avoid

## Step 5: Recommended Additional Plugins

For enhanced development, also install:

```
/plugin marketplace add obra/superpowers-marketplace
/plugin install superpowers@superpowers-marketplace
```

This adds TDD enforcement, planning, and review skills.

## Verification Complete

Once all steps pass, you're ready for RAE development. The `enforce-guidelines` skill will auto-activate before code tasks.

## If Installation Fails

1. Check network connectivity
2. Verify Claude Code version is recent
3. Try manual marketplace add with full URL
4. See `troubleshooting.md` for more help
