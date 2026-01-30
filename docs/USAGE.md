# Reproducible Agent Environment (RAE) - Usage Guide

## Overview

RAE provides standardized AI agent configurations across projects. It supports Claude Code with shared skills, SOPs, and coding standards.

## Prerequisites

- Docker (for devcontainers)
- VS Code with Remote Containers extension
- Claude Code CLI credentials configured locally

## Quick Start

### Option 1: Devcontainer (Recommended)

1. Copy the devcontainer configuration to your project:

```bash
mkdir -p .devcontainer
curl -fsSL https://raw.githubusercontent.com/peabody124/reproducible_agent_environment/main/.devcontainer/devcontainer.json -o .devcontainer/devcontainer.json
```

2. Open in VS Code and click "Reopen in Container"

3. The bootstrap script runs automatically, setting up:
   - Global agent instructions
   - Guidelines directory
   - Shared skills

### Option 2: Manual Setup

Run the bootstrap script directly:

```bash
curl -fsSL https://raw.githubusercontent.com/peabody124/reproducible_agent_environment/main/scripts/bootstrap.sh | bash
```

Or with a specific version:

```bash
RAE_VERSION=v1.0.0 curl -fsSL https://raw.githubusercontent.com/peabody124/reproducible_agent_environment/main/scripts/bootstrap.sh | bash
```

## Directory Structure After Bootstrap

```
your-project/
├── .claude/
│   └── GLOBAL_INSTRUCTIONS.md    # Global agent config (synced from RAE)
├── CLAUDE.md                     # Project-specific agent instructions
├── guidelines/
│   ├── coding-standards.md       # Core coding rules
│   ├── python-standards.md       # Python-specific rules
│   ├── git-workflow.md           # Git discipline
│   └── anti-patterns.md          # "Slop" to avoid
└── .rae-version                  # Current RAE version
```

## Upgrading

To upgrade to a newer RAE version:

```bash
# Upgrade to latest
./scripts/sync.sh

# Upgrade to specific version
./scripts/sync.sh v1.2.0

# Or using environment variable
RAE_VERSION=v1.2.0 ./scripts/sync.sh
```

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
| `/deslop` | Clean AI-generated slop from staged changes |
| `/consult-guidelines` | Review relevant guidelines for current task |
| `/config-improvement` | Propose improvements to upstream RAE |

## Proposing Improvements

When you discover a better pattern:

1. Verify it works in your project
2. Check if it's universal or project-specific
3. If universal, use `/config-improvement` or manually create a PR
4. After merge, run `./scripts/sync.sh` to get the improvement

See `sops/propose-upstream.sop.md` for the full workflow.

## Troubleshooting

### Credentials not working in container

Ensure your local credential directories exist and have correct permissions:

```bash
ls -la ~/.anthropic
```

The devcontainer mounts these directories read-only.

### Skills not loading

Re-run bootstrap if needed:

```bash
./scripts/bootstrap.sh
```

### Sync fails

Check network connectivity and that the RAE repository is accessible:

```bash
curl -I https://raw.githubusercontent.com/peabody124/reproducible_agent_environment/main/CLAUDE.md
```
