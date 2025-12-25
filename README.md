# Reproducible Agent Environment (RAE)

Standardized AI agent configurations for consistent development across projects. Supports both **Claude Code** and **Gemini CLI** with shared skills, SOPs, and coding standards.

## Why RAE?

Just as Docker standardizes runtime environments, RAE standardizes the context and tooling for AI agents working on your code. This means:

- **Consistent behavior** across projects and agents
- **Shared improvements** flow to all projects via sync
- **Cross-agent compatibility** using skillz format
- **Version-controlled workflows** that evolve with your practices

## Quick Start

### In a new project

```bash
curl -fsSL https://raw.githubusercontent.com/peabody124/reproducible_agent_environment/main/scripts/bootstrap.sh | bash
```

### With devcontainers

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

## Cross-Agent Compatibility

Skills use the [skillz](https://github.com/intellectronica/skillz) format with `SKILL.md` files, compatible with:

- **Claude Code** — Native skill support
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
