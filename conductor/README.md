# Conductor Context Directory

This directory contains context files for [Gemini Conductor](https://github.com/gemini-cli-extensions/conductor) and cross-agent workflow support.

## Purpose

These files provide persistent project context that agents can reference:

- **product.md** — Product vision, goals, and non-goals
- **workflow.md** — Development workflow preferences and checklists
- **tech-stack.md** — Technology choices and constraints

## Cross-Agent Compatibility

While Conductor is a Gemini CLI extension, the context files in this directory are plain markdown and can be referenced by any agent:

- **Claude Code** — Reference these files in CLAUDE.md or read them directly
- **Gemini CLI** — Use `conductor setup` to initialize, then `conductor new track` for features
- **Other agents** — Read the markdown files for context

## Integration with RAE

The bootstrap script creates starter templates for these files. Customize them for your project:

```markdown
# product.md
## Vision
A biomechanics analysis tool that...

## Goals
1. Accurate motion capture processing
2. Real-time feedback
3. Accessible to clinicians

## Non-Goals
- Gaming or entertainment applications
- Consumer mobile apps
```

## Workflow with OpenCode-Conductor-Bridge

For projects using OpenCode, the [opencode-conductor-bridge](https://github.com/bardusco/opencode-conductor-bridge) enables the same Conductor workflows:

1. Context stored in `conductor/` works across tools
2. Commands translate between platforms
3. Styleguides and templates are portable

This means your project context is portable across Claude, Gemini, and OpenCode.
