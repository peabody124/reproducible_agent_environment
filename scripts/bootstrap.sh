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

# 1. Install Claude Code CLI (native binary)
echo ""
echo "==> Checking Claude Code CLI..."
if command -v claude &> /dev/null; then
    echo "    ✓ Claude Code already installed"
else
    echo "    Installing Claude Code via native binary..."
    curl -fsSL https://claude.ai/install.sh | bash
    export PATH="$HOME/.local/bin:$PATH"
    if command -v claude &> /dev/null; then
        echo "    ✓ Claude Code installed"
    else
        echo "    Claude Code install failed — install manually"
    fi
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

# 4. Pull global agent instructions
echo ""
echo "==> Pulling global agent instructions..."
curl -fsSL "$RAE_REPO/$RAE_VERSION/CLAUDE.md" -o .claude/GLOBAL_INSTRUCTIONS.md

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

# 6. Record version
echo ""
echo "==> Recording version..."
echo "$RAE_VERSION" > .rae-version

# 8. Add to .gitignore if not present
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
echo "║  2. Start working with 'claude' CLI                        ║"
echo "║                                                            ║"
echo "║  To upgrade: RAE_VERSION=<tag> ./scripts/sync.sh           ║"
echo "╚════════════════════════════════════════════════════════════╝"
