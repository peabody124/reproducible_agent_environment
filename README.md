# Reproducible Agent Environment (RAE)

Standardized AI agent configurations for consistent development across projects. Supports both **Claude Code** and **Gemini CLI** with shared skills, SOPs, and coding standards.

## Why RAE?

Just as Docker standardizes runtime environments, RAE standardizes the context and tooling for AI agents working on your code. This means:

- **Consistent behavior** across projects and agents
- **Shared improvements** flow to all projects via sync
- **Cross-agent compatibility** using skillz format
- **Version-controlled workflows** that evolve with your practices

## Installation

### Option 1: Claude Code Plugin (Recommended)

Install RAE as a native Claude Code plugin:

```bash
# In Claude Code, add the marketplace
/plugin marketplace add peabody124/reproducible_agent_environment

# Install the RAE plugin
/plugin install rae@reproducible_agent_environment
```

### Option 2: Full Bootstrap

Sets up everything including guidelines, conductor context, and cross-agent compatibility:

```bash
curl -fsSL https://raw.githubusercontent.com/peabody124/reproducible_agent_environment/main/scripts/bootstrap.sh | bash
```

This will:
- Install the RAE Claude Code plugin (if claude CLI available)
- Set up guidelines/ directory
- Configure Gemini CLI extensions
- Install skills to ~/.skillz for MCP compatibility

### Option 3: With Devcontainers

Copy `.devcontainer/devcontainer.json` to your project and reopen in container.

## What's Included

### Guidelines (`guidelines/`)

| File | Purpose |
|------|---------|
| `coding-standards.md` | TDD mandate, DRY, fail-fast, configuration |
| `python-standards.md` | ruff, typing, paths, project layout |
| `git-workflow.md` | Staging discipline, commit standards |
| `anti-patterns.md` | "Slop" patterns to avoid |

### Skills (`skills/`)

| Skill | Purpose |
|-------|---------|
| `deslop` | Clean AI-generated artifacts before commit |
| `consult-guidelines` | Review relevant guidelines for task |
| `config-improvement` | Propose improvements upstream |

### SOPs (`sops/`)

| SOP | Purpose |
|-----|---------|
| `propose-upstream.sop.md` | Workflow for contributing improvements |
| `pre-commit-checklist.sop.md` | Quality checks before every commit |

### Templates (`templates/`)

- `pyproject.toml` — Standard Python project configuration
- `.gitignore` — Common ignores including scraps/

## Architecture

```
┌─────────────────────────────────────────┐
│  Project CLAUDE.md (project-specific)   │  ← Local overrides, commands
├─────────────────────────────────────────┤
│  .claude/GLOBAL_INSTRUCTIONS.md         │  ← Universal rules (synced)
├─────────────────────────────────────────┤
│  guidelines/*.md                        │  ← Detailed standards (synced)
└─────────────────────────────────────────┘
```

**Upgrade flow:** Agents discovering improvements propose PRs upstream. After merge, all projects get the improvement via `sync.sh`.

## Upgrading

```bash
# Latest
./scripts/sync.sh

# Specific version
./scripts/sync.sh v1.0.0
```

Or update the Claude Code plugin:

```bash
# In Claude Code
/plugin update rae@reproducible_agent_environment
```

## Cross-Agent Compatibility

RAE supports multiple installation methods:

| Method | Target | Location |
|--------|--------|----------|
| Claude Code Plugin | Claude Code native | Managed by plugin system |
| ~/.skillz/ | Gemini CLI, MCP servers | `~/.skillz/*/SKILL.md` |
| ~/.claude/skills/ | Claude Code global | `~/.claude/skills/*/SKILL.md` |

Skills use the [skillz](https://github.com/intellectronica/skillz) format with `SKILL.md` files, compatible with:

- **Claude Code** — Native plugin support + skillz MCP
- **Gemini CLI** — Via [gemini-cli-skillz](https://github.com/intellectronica/gemini-cli-skillz) extension

## Conductor Integration

For Gemini CLI, [Conductor](https://github.com/gemini-cli-extensions/conductor) provides context-driven development. RAE bootstraps a `conductor/` directory with:

- `product.md` — Product vision and goals
- `workflow.md` — Development workflow preferences

## Contributing

Discovered a better pattern? Use the `/config-improvement` skill or:

1. Fork this repository
2. Create a branch: `improve/<area>-<change>`
3. Make your improvement with rationale
4. Open a PR with before/after examples

## Research References

- [Gemini Conductor](https://github.com/gemini-cli-extensions/conductor) — Context-driven development
- [Strands Agent SOPs](https://github.com/strands-agents/agent-sop) — Markdown workflow format
- [Skillz](https://github.com/intellectronica/skillz) — MCP server for cross-agent skills
- [gemini-cli-skillz](https://github.com/intellectronica/gemini-cli-skillz) — Gemini extension for skillz
- [opencode-conductor-bridge](https://github.com/bardusco/opencode-conductor-bridge) — Cross-platform Conductor workflows

## License

MIT
