# Reproducible Agent Environment (RAE) - Usage Guide

## Overview

RAE provides standardized AI agent configurations across projects. It supports Claude Code with shared skills, SOPs, and coding standards.

For installation, see the [README](../README.md).

## Local Overrides

Add project-specific instructions to `CLAUDE.md` below the global include:

```markdown
# Project Agent Instructions

<!-- Global instructions loaded from .claude/GLOBAL_INSTRUCTIONS.md -->

## Project Context

This project is a biomechanics analysis tool using JAX...

## Project-Specific Commands

- `make analyze` — Run motion capture analysis
- `make report` — Generate PDF report

## Local Overrides

<!-- Override: Using dict.get for external API responses -->
For this project, we allow dict.get when parsing external API responses
because the schema is not guaranteed.
```

## Available Skills

Skills are available through the Claude Code plugin:

| Skill | Description |
|-------|-------------|
| `/enforce-guidelines` | Ensures work follows RAE standards (auto-activates) |
| `/deslop` | Clean AI-generated slop from staged changes |
| `/consult-guidelines` | Review relevant guidelines for current task |
| `/scaffold-repo` | Create new repos with correct structure |
| `/config-improvement` | Propose improvements to upstream RAE |

## Proposing Improvements

When you discover a better pattern:

1. Verify it works in your project
2. Check if it's universal or project-specific
3. If universal, use `/config-improvement` or manually create a PR
4. After merge, run `./scripts/sync.sh` to get the improvement

## Troubleshooting

### Skills not loading

1. Check plugin is installed: `/plugin list`
2. Re-install the plugin if needed
3. Restart Claude Code session

### Sync fails

Check network connectivity and that the RAE repository is accessible:

```bash
curl -I https://raw.githubusercontent.com/peabody124/reproducible_agent_environment/main/CLAUDE.md
```
