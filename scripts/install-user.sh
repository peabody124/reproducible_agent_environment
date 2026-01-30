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
echo "║  This installs to ~/.claude/ only                           ║"
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

# 3. Cache guidelines in ~/.claude/rae/ for reference
echo ""
echo "==> Caching guidelines to ~/.claude/rae/..."
mkdir -p ~/.claude/rae/guidelines
mkdir -p ~/.claude/rae/templates

for guide in coding-standards python-standards repo-structure git-workflow anti-patterns; do
    curl -fsSL "$RAE_REPO/$RAE_VERSION/guidelines/${guide}.md" -o ~/.claude/rae/guidelines/${guide}.md
done
curl -fsSL "$RAE_REPO/$RAE_VERSION/templates/pyproject.toml" -o ~/.claude/rae/templates/pyproject.toml
echo "    ✓ Guidelines cached to ~/.claude/rae/"

# 4. Install Python LSP (pyright) for code intelligence
echo ""
echo "==> Installing Python LSP (pyright)..."
if command -v npm &> /dev/null; then
    npm install -g pyright 2>/dev/null && echo "    ✓ pyright installed via npm" || echo "    pyright already installed or install failed"
elif command -v pip &> /dev/null; then
    pip install pyright 2>/dev/null && echo "    ✓ pyright installed via pip" || echo "    pyright already installed or install failed"
else
    echo "    Neither npm nor pip found, skipping pyright install"
    echo "    Install manually: npm install -g pyright"
fi

# 5. Enable LSP tool in shell profile
echo ""
echo "==> Configuring ENABLE_LSP_TOOL..."
SHELL_PROFILE=""
if [ -f ~/.zshrc ]; then
    SHELL_PROFILE=~/.zshrc
elif [ -f ~/.bashrc ]; then
    SHELL_PROFILE=~/.bashrc
fi

if [ -n "$SHELL_PROFILE" ]; then
    if ! grep -q "ENABLE_LSP_TOOL" "$SHELL_PROFILE" 2>/dev/null; then
        echo "" >> "$SHELL_PROFILE"
        echo "# Claude Code LSP support (added by RAE)" >> "$SHELL_PROFILE"
        echo "export ENABLE_LSP_TOOL=1" >> "$SHELL_PROFILE"
        echo "    ✓ Added ENABLE_LSP_TOOL=1 to $SHELL_PROFILE"
    else
        echo "    ✓ ENABLE_LSP_TOOL already configured"
    fi
else
    echo "    No shell profile found, add manually: export ENABLE_LSP_TOOL=1"
fi

# Also export for current session
export ENABLE_LSP_TOOL=1

# 6. Record version
echo "$RAE_VERSION" > ~/.claude/rae/.version

echo ""
echo "╔════════════════════════════════════════════════════════════╗"
echo "║  RAE User Installation Complete!                           ║"
echo "║                                                            ║"
echo "║  Installed:                                                ║"
echo "║  - Claude plugin: rae@reproducible_agent_environment       ║"
echo "║  - Guidelines: ~/.claude/rae/guidelines/                   ║"
echo "║  - Python LSP: pyright (ENABLE_LSP_TOOL=1)                 ║"
echo "║                                                            ║"
echo "║  No files were added to the current directory.             ║"
echo "║                                                            ║"
echo "║  To create a new project: /scaffold-repo                   ║"
echo "║  Restart shell or run: source ~/.bashrc (or ~/.zshrc)      ║"
echo "╚════════════════════════════════════════════════════════════╝"
