#!/bin/bash
set -euo pipefail

# Reproducible Agent Environment (RAE) Bootstrap Script
# This script sets up a project with RAE configurations

RAE_REPO="${RAE_REPO:-https://raw.githubusercontent.com/peabody124/reproducible_agent_environment}"
RAE_REPO_ID="${RAE_REPO_ID:-peabody124/reproducible_agent_environment}"
RAE_VERSION="${RAE_VERSION:-main}"

echo "╔════════════════════════════════════════════════════════════╗"
echo "║  Reproducible Agent Environment (RAE) Bootstrap            ║"
echo "║  Version: $RAE_VERSION                                     ║"
echo "╚════════════════════════════════════════════════════════════╝"

# 1. Install agent CLIs
echo ""
echo "==> Installing agent CLIs..."
if command -v npm &> /dev/null; then
    npm install -g @anthropic-ai/claude-code 2>/dev/null || echo "    Claude Code already installed or npm not available"
fi

if command -v pip &> /dev/null; then
    pip install --quiet gemini-cli 2>/dev/null || echo "    Gemini CLI already installed or pip issue"
fi

# 2. Install RAE as Claude Code plugin (if claude CLI available)
echo ""
echo "==> Installing RAE as Claude Code plugin..."
if command -v claude &> /dev/null; then
    # Add this repo as a marketplace
    if claude marketplace add "$RAE_REPO_ID" 2>/dev/null; then
        echo "    ✓ RAE marketplace registered"
    else
        echo "    RAE marketplace already registered or unavailable"
    fi

    # Install the RAE plugin
    if claude plugin install rae@reproducible_agent_environment --scope user 2>/dev/null; then
        echo "    ✓ RAE plugin installed"
    else
        echo "    RAE plugin already installed or unavailable"
    fi
else
    echo "    Claude Code CLI not found, skipping plugin install"
    echo "    After installing Claude Code, run:"
    echo "      /plugin marketplace add $RAE_REPO_ID"
    echo "      /plugin install rae@reproducible_agent_environment"
fi

# 3. Create directory structure
echo ""
echo "==> Setting up directory structure..."
mkdir -p .claude
mkdir -p guidelines
mkdir -p conductor

# 4. Pull global agent instructions
echo ""
echo "==> Pulling global agent instructions..."
curl -fsSL "$RAE_REPO/$RAE_VERSION/CLAUDE.md" -o .claude/GLOBAL_INSTRUCTIONS.md
curl -fsSL "$RAE_REPO/$RAE_VERSION/GEMINI.md" -o .gemini_context.md 2>/dev/null || true

# Pull guidelines
echo "==> Pulling guidelines..."
for guide in coding-standards python-standards repo-structure git-workflow anti-patterns; do
    curl -fsSL "$RAE_REPO/$RAE_VERSION/guidelines/${guide}.md" -o "guidelines/${guide}.md"
done

# 5. Set up project CLAUDE.md if it doesn't exist
if [ ! -f CLAUDE.md ]; then
    echo ""
    echo "==> Creating project CLAUDE.md..."
    cat > CLAUDE.md << 'HEREDOC'
# Project Agent Instructions

<!-- Global instructions are loaded from .claude/GLOBAL_INSTRUCTIONS.md -->
<!-- Add project-specific instructions below -->

## Project Context

<!-- Describe your project here -->

## Project-Specific Commands

<!-- Add project-specific commands here -->

## Local Overrides

<!-- Document any local overrides and why they exist -->
HEREDOC
fi

# 6. Install shared skills to ~/.skillz (Gemini/MCP compatibility)
echo ""
echo "==> Installing shared skills to ~/.skillz (Gemini compatibility)..."
mkdir -p ~/.skillz/deslop
mkdir -p ~/.skillz/consult-guidelines
mkdir -p ~/.skillz/config-improvement
mkdir -p ~/.skillz/enforce-guidelines
mkdir -p ~/.skillz/scaffold-repo

curl -fsSL "$RAE_REPO/$RAE_VERSION/skills/deslop/SKILL.md" -o ~/.skillz/deslop/SKILL.md
curl -fsSL "$RAE_REPO/$RAE_VERSION/skills/consult-guidelines/SKILL.md" -o ~/.skillz/consult-guidelines/SKILL.md
curl -fsSL "$RAE_REPO/$RAE_VERSION/skills/config-improvement/SKILL.md" -o ~/.skillz/config-improvement/SKILL.md
curl -fsSL "$RAE_REPO/$RAE_VERSION/skills/enforce-guidelines/SKILL.md" -o ~/.skillz/enforce-guidelines/SKILL.md
curl -fsSL "$RAE_REPO/$RAE_VERSION/skills/scaffold-repo/SKILL.md" -o ~/.skillz/scaffold-repo/SKILL.md

# 7. Install Gemini extensions (if gemini CLI is available)
echo ""
echo "==> Installing Gemini extensions..."
if command -v gemini &> /dev/null; then
    gemini extensions install gemini-cli-extensions/conductor --auto-update 2>/dev/null || echo "    Conductor already installed or unavailable"
    gemini extensions install intellectronica/gemini-cli-skillz 2>/dev/null || echo "    gemini-cli-skillz already installed or unavailable"
else
    echo "    Gemini CLI not found, skipping extension installation"
fi

# 8. Set up conductor context if not exists
if [ ! -f conductor/product.md ]; then
    echo ""
    echo "==> Setting up Conductor context..."
    cat > conductor/product.md << 'HEREDOC'
# Product Context

## Vision

<!-- Describe the product vision -->

## Goals

<!-- List primary goals -->

## Non-Goals

<!-- What this project explicitly does NOT do -->
HEREDOC
fi

if [ ! -f conductor/workflow.md ]; then
    cat > conductor/workflow.md << 'HEREDOC'
# Workflow Preferences

## Development Flow

1. Understand requirements
2. Write failing test (TDD)
3. Implement minimal solution
4. Refactor and clean up
5. Run deslop before commit

## Review Checklist

- [ ] Tests pass
- [ ] Ruff format/check clean
- [ ] No slop patterns
- [ ] Atomic commits
HEREDOC
fi

# 9. Record version
echo ""
echo "==> Recording version..."
echo "$RAE_VERSION" > .rae-version

# 10. Add to .gitignore if not present
if [ -f .gitignore ]; then
    grep -q ".rae-version" .gitignore || echo ".rae-version" >> .gitignore
else
    echo ".rae-version" > .gitignore
fi

echo ""
echo "╔════════════════════════════════════════════════════════════╗"
echo "║  RAE Bootstrap Complete!                                   ║"
echo "║                                                            ║"
echo "║  Version: $RAE_VERSION                                     ║"
echo "║                                                            ║"
echo "║  Next steps:                                               ║"
echo "║  1. Edit CLAUDE.md with project-specific instructions      ║"
echo "║  2. Edit conductor/product.md with your product context    ║"
echo "║  3. Start working with 'claude' or 'gemini' CLI            ║"
echo "║                                                            ║"
echo "║  To upgrade: RAE_VERSION=<tag> ./scripts/sync.sh           ║"
echo "╚════════════════════════════════════════════════════════════╝"
