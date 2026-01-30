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

## Step 5: Install pyright-lsp Plugin

For Python code intelligence (type checking, go-to-definition):

```
/plugin install pyright-lsp@claude-plugin-directory
```

Verify pyright is available:

```bash
pyright --version
```

If pyright is not installed as a binary, install it: `pip install pyright`

## Step 6: Install Official Claude Plugins

Install the remaining official Claude plugins:

```
/plugin install code-review@claude-plugin-directory
/plugin install feature-dev@claude-plugin-directory
/plugin install code-simplifier@claude-plugin-directory
/plugin install plugin-dev@claude-plugin-directory
```

## Step 7: Install Beads

Beads enables bead-driven development workflows:

```bash
# Install beads CLI
curl -fsSL https://raw.githubusercontent.com/steveyegge/beads/main/scripts/install.sh | bash

# Install uv (if not already available)
curl -LsSf https://astral.sh/uv/install.sh | sh
```

Then in Claude Code:

```
/plugin marketplace add steveyegge/beads
/plugin install beads
```

Set up beads for Claude Code:

```bash
bd setup claude
```

## Step 8: Install Superpowers

For TDD enforcement, planning, and review skills:

```
/plugin marketplace add obra/superpowers-marketplace
/plugin install superpowers@superpowers-marketplace
```

## Verification Complete

Once all steps pass, you're ready for RAE development. The `enforce-guidelines` skill will auto-activate before code tasks.

## If Installation Fails

1. Check network connectivity
2. Verify Claude Code version is recent
3. Try manual marketplace add with full URL
4. See `troubleshooting.md` for more help
