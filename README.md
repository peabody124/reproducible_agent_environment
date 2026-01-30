# Reproducible Agent Environment (RAE)

Standardized AI agent configurations for consistent development across projects. Provides shared skills and coding standards for **Claude Code**.

## Why RAE?

Just as Docker standardizes runtime environments, RAE standardizes the context and tooling for AI agents working on your code. This means:

- **Consistent behavior** across projects
- **Shared improvements** flow to all projects via plugin updates
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

This installs Claude Code (native binary), pyright, the RAE plugin, and the full recommended plugin suite (pyright-lsp, official Claude plugins, beads, superpowers).

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

### Scaffolding a New Project

Use the `/scaffold-repo` skill to create a properly structured Python project:

```
/scaffold-repo my-project A tool for analyzing motion capture data
```

This creates the full RAE-compliant project structure: `src/` layout, `pyproject.toml`, tests, `.gitignore`, and optionally a devcontainer. See `skills/scaffold-repo/SKILL.md` for the complete reference.

### Devcontainers

**New project:** Use `/scaffold-repo` with the devcontainer option, or copy `.devcontainer/` from this repo into your project. No custom Dockerfile needed — everything is installed via `postCreateCommand`.

**Existing devcontainer:** Add these fields to your `devcontainer.json`:

```jsonc
{
  // Mount host Claude config (create first: mkdir -p ~/.claude)
  "mounts": [
    "source=${localEnv:HOME}/.claude,target=/home/vscode/.claude,type=bind,consistency=cached"
  ],

  // Install RAE + full plugin suite after container creation
  "postCreateCommand": "curl -fsSL https://raw.githubusercontent.com/peabody124/reproducible_agent_environment/main/scripts/install-user.sh | bash",

  // Required environment variables
  "containerEnv": {
    "RAE_VERSION": "main",
    "CLAUDE_CONFIG_DIR": "/home/vscode/.claude",
    "ENABLE_LSP_TOOL": "1"
  }
}
```

The `install-user.sh` script handles everything: Claude Code, pyright, RAE plugin, and the full recommended plugin suite.

See `.devcontainer/` in this repo as the canonical reference.

## What's Included

### Skills

| Skill | Purpose | Activation |
|-------|---------|------------|
| `enforce-guidelines` | Ensures all work follows RAE guidelines | **Auto** — before any code task |
| `scaffold-repo` | Initialize new repo with correct structure | Manual |
| `deslop` | Clean AI-generated slop from code changes | Manual |
| `consult-guidelines` | Review relevant guidelines for task | Manual |
| `config-improvement` | Propose improvements upstream | Manual |
| `bead-driven-development` | Orchestrate planning + execution with beads tracking | Manual |
| `investigation` | Scaffold structured research in scratch/ | Manual |
| `datajoint-biomechanics-schema` | DataJoint pipeline schema reference | Auto — domain queries |
| `pose-datajoint` | Python code patterns for DataJoint pose queries | Auto — domain queries |

### Guidelines (bundled in `skills/enforce-guidelines/references/`)

| File | Purpose |
|------|---------|
| `coding-standards.md` | TDD mandate, DRY, fail-fast, configuration |
| `python-standards.md` | ruff (120 chars), typing, coverage ≥80% |
| `repo-structure.md` | Repository layout, pyproject.toml requirements |
| `git-workflow.md` | Staging discipline, commit standards |
| `anti-patterns.md` | "Slop" patterns to avoid |
| `pre-commit-checklist.md` | Pre-commit verification workflow |

### SessionStart Hook

RAE includes a `SessionStart` hook that automatically loads the core guidelines (coding-standards, python-standards, git-workflow, anti-patterns, pre-commit-checklist) into every Claude Code session. No manual consultation needed — the standards are always in context.

### Bead-Driven Development Prerequisites

The `bead-driven-development` skill requires additional plugins (installed automatically by `install-user.sh`):

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

## Upgrading

Re-run the install script or update the plugin directly:

```bash
# User-level: re-run install
curl -fsSL https://raw.githubusercontent.com/peabody124/reproducible_agent_environment/main/scripts/install-user.sh | bash

# Or update the plugin in Claude Code
/plugin update rae@reproducible_agent_environment
```

## Contributing

Discovered a better pattern? Use the `/config-improvement` skill or:

1. Fork this repository
2. Create a branch: `improve/<area>-<change>`
3. Make your improvement with rationale
4. Open a PR with before/after examples

## Research References

- [obra/superpowers](https://github.com/obra/superpowers) — Skill-driven TDD enforcement
