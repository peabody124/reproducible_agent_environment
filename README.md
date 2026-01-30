# Reproducible Agent Environment (RAE)

Standardized AI agent configurations for consistent development across projects. Provides shared skills, SOPs, and coding standards for **Claude Code**.

## Why RAE?

Just as Docker standardizes runtime environments, RAE standardizes the context and tooling for AI agents working on your code. This means:

- **Consistent behavior** across projects
- **Shared improvements** flow to all projects via sync
- **Version-controlled workflows** that evolve with your practices
- **Enforced guidelines** — not suggestions, requirements

## Installation

### Install the Plugin

RAE is distributed as a Claude Code plugin. No files are added to your repos.

**Interactive (in Claude Code):**

```
/plugin marketplace add peabody124/reproducible_agent_environment
/plugin install rae@reproducible_agent_environment
```

**Scripted (one-liner):**

```bash
curl -fsSL https://raw.githubusercontent.com/peabody124/reproducible_agent_environment/main/scripts/install-user.sh | bash
```

This installs Claude Code (native binary), the RAE plugin, and the full recommended plugin suite (pyright-lsp, official Claude plugins, beads, superpowers).

### Recommended Plugins

The install script installs all of these automatically. For manual installation:

```
# Official Claude plugins
/plugin install pyright-lsp@claude-plugin-directory
/plugin install code-review@claude-plugin-directory
/plugin install feature-dev@claude-plugin-directory
/plugin install code-simplifier@claude-plugin-directory
/plugin install plugin-dev@claude-plugin-directory

# Beads (bead-driven development)
curl -fsSL https://raw.githubusercontent.com/steveyegge/beads/main/scripts/install.sh | bash
curl -LsSf https://astral.sh/uv/install.sh | sh
/plugin marketplace add steveyegge/beads
/plugin install beads
bd setup claude

# Superpowers (TDD enforcement, planning, review)
/plugin marketplace add obra/superpowers-marketplace
/plugin install superpowers@superpowers-marketplace
```

### Devcontainers

**New project:** Copy `.devcontainer/` from this repo into your project. It includes a Dockerfile (Python 3.11, ripgrep, Claude Code, pyright) and a devcontainer.json that runs `install-user.sh` on creation.

**Existing devcontainer:** Merge these pieces into your configuration:

1. **Dockerfile** — add `curl -fsSL https://claude.ai/install.sh | bash` and `pip install pyright` (see `.devcontainer/Dockerfile` for the full reference)
2. **Mounts** — bind `~/.claude` into the container for credential access
3. **postCreateCommand** — run `install-user.sh` to install the full plugin suite
4. **containerEnv** — set `CLAUDE_CONFIG_DIR` to the mounted `.claude` path and `ENABLE_LSP_TOOL` to `1`

See `.devcontainer/` in this repo as the canonical reference.

### Vendored Guidelines (Optional)

For repos where you want guidelines checked into version control:

```bash
curl -fsSL https://raw.githubusercontent.com/peabody124/reproducible_agent_environment/main/scripts/bootstrap.sh | bash
```

This adds `guidelines/` and `.claude/GLOBAL_INSTRUCTIONS.md` to the repo. Use this only for repos you own.

## What's Included

### Guidelines (`guidelines/`)

| File | Purpose |
|------|---------|
| `coding-standards.md` | TDD mandate, DRY, fail-fast, configuration |
| `python-standards.md` | ruff (120 chars), typing, coverage ≥80% |
| `repo-structure.md` | Repository layout, pyproject.toml requirements |
| `git-workflow.md` | Staging discipline, commit standards |
| `anti-patterns.md` | "Slop" patterns to avoid |

### Skills (`skills/`)

| Skill | Purpose | Activation |
|-------|---------|------------|
| `enforce-guidelines` | Ensures all work follows RAE guidelines | **Auto** — before any code task |
| `scaffold-repo` | Initialize new repo with correct structure | Manual |
| `deslop` | Clean AI-generated slop from code changes | Manual |
| `consult-guidelines` | Review relevant guidelines for task | Manual |
| `config-improvement` | Propose improvements upstream | Manual |
| `bead-driven-development` | Orchestrate planning + execution with beads tracking | Manual |

### Bead-Driven Development Prerequisites

The `bead-driven-development` skill requires additional plugins:

```bash
# Install beads CLI and plugin
curl -fsSL https://raw.githubusercontent.com/steveyegge/beads/main/scripts/install.sh | bash
curl -LsSf https://astral.sh/uv/install.sh | sh
/plugin marketplace add steveyegge/beads
/plugin install beads

# Install superpowers (for writing-plans, executing-plans, investigation)
/plugin marketplace add obra/superpowers-marketplace
/plugin install superpowers@superpowers-marketplace

# Initialize beads in your repo
bd init
```

### Agent Self-Setup (`.agent_setup_instructions/`)

Instructions for agents to self-configure:
- `setup-checklist.md` — Step-by-step plugin installation
- `verify-installation.md` — How to confirm RAE works
- `troubleshooting.md` — Common issues and fixes

## Key Standards

### Python Projects

- **Line length:** 120 characters (not 80, not 100)
- **Coverage:** ≥80% required (enforced by pytest-cov)
- **Layout:** `src/` directory with `tests/` mirroring structure
- **Dependencies:** pytest, ruff in `[project.optional-dependencies] dev`

```toml
[project.optional-dependencies]
dev = ["pytest>=8.0", "pytest-cov>=4.0", "ruff>=0.8"]

[tool.coverage.report]
fail_under = 80
```

### Workflow Enforcement

RAE skills are inspired by [obra/superpowers](https://github.com/obra/superpowers):

- **Guidelines are mandatory** — `enforce-guidelines` activates before any code task
- **TDD is the default** — tests before implementation
- **Verification required** — `ruff format && ruff check && pytest` before completion

## Scripts

| Script | Purpose | Modifies Repo? |
|--------|---------|----------------|
| `install-user.sh` | User-level installation (RAE + full plugin suite) | No |
| `bootstrap.sh` | Full repo setup with vendored guidelines | Yes |
| `sync.sh` | Update RAE to latest version | Depends |

## Upgrading

Re-run the install script or update the plugin directly:

```bash
# User-level: re-run install
curl -fsSL https://raw.githubusercontent.com/peabody124/reproducible_agent_environment/main/scripts/install-user.sh | bash

# Repo-level: sync script
./scripts/sync.sh

# Or update the plugin in Claude Code
/plugin update rae@rae-marketplace
```

## Contributing

Discovered a better pattern? Use the `/config-improvement` skill or:

1. Fork this repository
2. Create a branch: `improve/<area>-<change>`
3. Make your improvement with rationale
4. Open a PR with before/after examples

## Research References

- [obra/superpowers](https://github.com/obra/superpowers) — Skill-driven TDD enforcement

## License

MIT
