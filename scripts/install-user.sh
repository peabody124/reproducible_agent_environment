#!/bin/bash
set -euo pipefail

# Reproducible Agent Environment (RAE) User-Level Installation
# This script installs RAE to user home directory ONLY - no repo pollution
#
# Use this for:
# - Dev container setup (postCreateCommand)
# - Personal workstation setup
# - Working on other people's repos without modifying them

RAE_REPO="${RAE_REPO:-https://raw.githubusercontent.com/peabody124/reproducible_agent_environment}"
RAE_REPO_ID="${RAE_REPO_ID:-peabody124/reproducible_agent_environment}"
RAE_VERSION="${RAE_VERSION:-main}"

echo "╔════════════════════════════════════════════════════════════╗"
echo "║  RAE User-Level Installation                               ║"
echo "║  Version: $RAE_VERSION                                     ║"
echo "║                                                            ║"
echo "║  This installs to ~/.claude/ and ~/.skillz/ only           ║"
echo "║  No files will be added to the current directory           ║"
echo "╚════════════════════════════════════════════════════════════╝"

# 1. Install Claude Code CLI (if npm available)
echo ""
echo "==> Checking Claude Code CLI..."
if command -v claude &> /dev/null; then
    echo "    ✓ Claude Code already installed"
elif command -v npm &> /dev/null; then
    echo "    Installing Claude Code..."
    npm install -g @anthropic-ai/claude-code 2>/dev/null || echo "    Could not install (may need sudo)"
else
    echo "    npm not found, skipping Claude Code CLI install"
fi

# 2. Install RAE as Claude Code plugin
echo ""
echo "==> Installing RAE plugin..."
if command -v claude &> /dev/null; then
    # Add marketplace
    if claude marketplace add "$RAE_REPO_ID" 2>/dev/null; then
        echo "    ✓ RAE marketplace registered"
    else
        echo "    RAE marketplace already registered or unavailable"
    fi

    # Install plugin
    if claude plugin install rae@reproducible_agent_environment --scope user 2>/dev/null; then
        echo "    ✓ RAE plugin installed"
    else
        echo "    RAE plugin already installed or unavailable"
    fi
else
    echo "    Claude Code CLI not found"
    echo "    After installing, run these commands in Claude Code:"
    echo "      /plugin marketplace add $RAE_REPO_ID"
    echo "      /plugin install rae@reproducible_agent_environment"
fi

# 3. Install skills to ~/.skillz (Gemini/MCP compatibility)
echo ""
echo "==> Installing skills to ~/.skillz..."
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
echo "    ✓ Skills installed to ~/.skillz/"

# 4. Cache guidelines in ~/.claude/rae/ for reference
echo ""
echo "==> Caching guidelines to ~/.claude/rae/..."
mkdir -p ~/.claude/rae/guidelines
mkdir -p ~/.claude/rae/templates

for guide in coding-standards python-standards repo-structure git-workflow anti-patterns; do
    curl -fsSL "$RAE_REPO/$RAE_VERSION/guidelines/${guide}.md" -o ~/.claude/rae/guidelines/${guide}.md
done
curl -fsSL "$RAE_REPO/$RAE_VERSION/templates/pyproject.toml" -o ~/.claude/rae/templates/pyproject.toml
echo "    ✓ Guidelines cached to ~/.claude/rae/"

# 5. Install Gemini extensions (if available)
echo ""
echo "==> Checking Gemini CLI..."
if command -v gemini &> /dev/null; then
    gemini extensions install gemini-cli-extensions/conductor --auto-update 2>/dev/null || echo "    Conductor already installed or unavailable"
    gemini extensions install intellectronica/gemini-cli-skillz 2>/dev/null || echo "    gemini-cli-skillz already installed or unavailable"
else
    echo "    Gemini CLI not found, skipping extensions"
fi

# 6. Record version
echo "$RAE_VERSION" > ~/.claude/rae/.version

echo ""
echo "╔════════════════════════════════════════════════════════════╗"
echo "║  RAE User Installation Complete!                           ║"
echo "║                                                            ║"
echo "║  Installed to:                                             ║"
echo "║  - Claude plugin: rae@reproducible_agent_environment       ║"
echo "║  - Skills: ~/.skillz/                                      ║"
echo "║  - Guidelines: ~/.claude/rae/guidelines/                   ║"
echo "║                                                            ║"
echo "║  No files were added to the current directory.             ║"
echo "║                                                            ║"
echo "║  To create a new project: /scaffold-repo                   ║"
echo "║  To verify setup: see .agent_setup_instructions/           ║"
echo "╚════════════════════════════════════════════════════════════╝"
