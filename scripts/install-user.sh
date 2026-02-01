#!/bin/bash
set -euo pipefail

# Reproducible Agent Environment (RAE) User-Level Installation
# This script installs RAE to user home directory ONLY - no repo pollution
#
# Use this for:
# - Dev container setup (postCreateCommand)
# - Personal workstation setup
# - Working on other people's repos without modifying them

RAE_REPO_ID="${RAE_REPO_ID:-peabody124/reproducible_agent_environment}"

echo "╔══════════════════════════════════════════════════════════╗"
echo "║  RAE User-Level Installation                            ║"
echo "║                                                         ║"
echo "║  This installs to ~/.claude/ only                       ║"
echo "║  No files will be added to the current directory        ║"
echo "╚══════════════════════════════════════════════════════════╝"

# 1. Install Claude Code CLI (native binary)
echo ""
echo "==> Checking Claude Code CLI..."
if command -v claude &> /dev/null; then
    echo "    ✓ Claude Code already installed"
else
    echo "    Installing Claude Code via native binary..."
    curl -fsSL https://claude.ai/install.sh | bash
    # Ensure it's on PATH for the rest of this script
    export PATH="$HOME/.local/bin:$PATH"
    if command -v claude &> /dev/null; then
        echo "    ✓ Claude Code installed"
    else
        echo "    Claude Code install failed — install manually"
    fi
fi

# 2. Install RAE as Claude Code plugin
echo ""
echo "==> Installing RAE plugin..."
if command -v claude &> /dev/null; then
    # Add marketplace (note: "plugin marketplace", not just "marketplace")
    if claude plugin marketplace add "$RAE_REPO_ID" 2>/dev/null; then
        echo "    ✓ RAE marketplace registered"
    else
        echo "    RAE marketplace already registered or unavailable"
    fi

    # Install plugin, or update if already installed
    if claude plugin install rae@rae-marketplace --scope user 2>/dev/null; then
        echo "    ✓ RAE plugin installed"
    elif claude plugin update rae@rae-marketplace 2>/dev/null; then
        echo "    ✓ RAE plugin updated"
    else
        echo "    RAE plugin install/update failed"
    fi
else
    echo "    Claude Code CLI not found"
    echo "    After installing, run these commands in Claude Code:"
    echo "      /plugin marketplace add $RAE_REPO_ID"
    echo "      /plugin install rae@rae-marketplace"
fi

# 3. Install uv (needed by pyright, beads MCP server, and general Python tooling)
echo ""
echo "==> Checking uv..."
if command -v uv &> /dev/null; then
    echo "    ✓ uv already installed"
else
    echo "    Installing uv..."
    curl -LsSf https://astral.sh/uv/install.sh | sh 2>/dev/null || echo "    uv install failed"
    # Source uv env so it's available for the rest of this script
    [ -f "$HOME/.local/bin/env" ] && source "$HOME/.local/bin/env"
    if command -v uv &> /dev/null; then
        echo "    ✓ uv installed"
    else
        export PATH="$HOME/.local/bin:$PATH"
    fi
fi

# 4. Install pyright binary (needed by pyright-lsp plugin)
echo ""
echo "==> Checking pyright..."
if command -v pyright &> /dev/null; then
    echo "    ✓ pyright already installed"
elif command -v uv &> /dev/null; then
    uv tool install pyright 2>/dev/null && echo "    ✓ pyright installed via uv" || echo "    pyright install via uv failed"
elif command -v pip &> /dev/null; then
    pip install pyright 2>/dev/null && echo "    ✓ pyright installed via pip" || echo "    pyright install failed — install manually: pip install pyright"
else
    echo "    Neither uv nor pip found, skipping pyright install"
    echo "    Install manually: pip install pyright"
fi

# 5. Install pyright-lsp plugin
echo ""
echo "==> Installing pyright-lsp plugin..."
if command -v claude &> /dev/null; then
    if claude plugin install pyright-lsp@claude-plugins-official --scope user 2>/dev/null; then
        echo "    ✓ pyright-lsp plugin installed"
    else
        echo "    pyright-lsp plugin already installed or unavailable"
    fi
else
    echo "    Claude Code CLI not found, skipping pyright-lsp install"
    echo "    After installing Claude Code, run:"
    echo "      /plugin install pyright-lsp@claude-plugins-official"
fi

# 6. Install official Claude plugins
echo ""
echo "==> Installing official Claude plugins..."
if command -v claude &> /dev/null; then
    for plugin in code-review feature-dev code-simplifier plugin-dev; do
        if claude plugin install "${plugin}@claude-plugins-official" --scope user 2>/dev/null; then
            echo "    ✓ ${plugin} plugin installed"
        else
            echo "    ${plugin} plugin already installed or unavailable"
        fi
    done
else
    echo "    Claude Code CLI not found, skipping official plugins"
fi

# 7. Install beads (CLI + marketplace plugin + Claude Code hooks)
echo ""
echo "==> Installing beads..."

# Install or update bd CLI
if command -v bd &> /dev/null; then
    echo "    ✓ beads CLI already installed ($(bd version --short 2>/dev/null || echo 'unknown version'))"
else
    echo "    Installing beads CLI..."
    curl -fsSL https://raw.githubusercontent.com/steveyegge/beads/main/scripts/install.sh | bash 2>/dev/null || echo "    beads CLI install failed"
    export PATH="$HOME/.local/bin:$HOME/go/bin:$PATH"
fi

# Install beads Claude Code plugin (adds /beads:* slash commands)
if command -v claude &> /dev/null; then
    claude plugin marketplace add steveyegge/beads 2>/dev/null || true
    if claude plugin install beads@beads-marketplace --scope user 2>/dev/null; then
        echo "    ✓ beads plugin installed"
    elif claude plugin update beads@beads-marketplace 2>/dev/null; then
        echo "    ✓ beads plugin updated"
    else
        echo "    beads plugin already installed or unavailable"
    fi
else
    echo "    Claude Code CLI not found, skipping beads plugin"
fi

# Set up Claude Code hooks (SessionStart → bd prime, PreCompact → bd sync)
if command -v bd &> /dev/null; then
    bd setup claude 2>/dev/null && echo "    ✓ beads Claude Code hooks configured" || true
else
    echo "    bd not found — beads hooks not configured"
fi

# 8. Install superpowers (marketplace + plugin)
echo ""
echo "==> Installing superpowers..."
if command -v claude &> /dev/null; then
    claude plugin marketplace add obra/superpowers-marketplace 2>/dev/null || true
    if claude plugin install superpowers@superpowers-marketplace --scope user 2>/dev/null; then
        echo "    ✓ superpowers plugin installed"
    else
        echo "    superpowers plugin already installed or unavailable"
    fi
else
    echo "    Claude Code CLI not found, skipping superpowers plugin"
fi

echo ""
echo "╔══════════════════════════════════════════════════════════╗"
echo "║  RAE User Installation Complete!                        ║"
echo "║                                                         ║"
echo "║  Installed:                                             ║"
echo "║  - Claude Code CLI (native binary)                      ║"
echo "║  - Plugin: rae@rae-marketplace                          ║"
echo "║  - Plugin: pyright-lsp@claude-plugins-official          ║"
echo "║  - Plugins: code-review, feature-dev,                   ║"
echo "║    code-simplifier, plugin-dev (official Claude)        ║"
echo "║  - Plugin: beads (bead-driven development)              ║"
echo "║  - Plugin: superpowers@superpowers-marketplace          ║"
echo "║                                                         ║"
echo "║  No files were added to the current directory.          ║"
echo "║                                                         ║"
echo "║  To create a new project: /scaffold-repo                ║"
echo "╚══════════════════════════════════════════════════════════╝"
