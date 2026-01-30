#!/bin/bash
set -euo pipefail

# Reproducible Agent Environment (RAE) Sync Script
# This script updates RAE configurations to a specified version

RAE_REPO="${RAE_REPO:-https://raw.githubusercontent.com/peabody124/reproducible_agent_environment}"
RAE_REPO_ID="${RAE_REPO_ID:-peabody124/reproducible_agent_environment}"
RAE_VERSION="${1:-${RAE_VERSION:-main}}"

echo "╔════════════════════════════════════════════════════════════╗"
echo "║  Syncing RAE to version: $RAE_VERSION                      ║"
echo "╚════════════════════════════════════════════════════════════╝"

# Check current version
CURRENT_VERSION="unknown"
if [ -f .rae-version ]; then
    CURRENT_VERSION=$(cat .rae-version)
fi
echo "Current version: $CURRENT_VERSION"
echo "Target version:  $RAE_VERSION"
echo ""

# 1. Update Claude Code plugin (if available)
echo "==> Updating Claude Code plugin..."
if command -v claude &> /dev/null; then
    if claude plugin update rae@reproducible_agent_environment 2>/dev/null; then
        echo "    ✓ RAE plugin updated"
    else
        echo "    RAE plugin update skipped (not installed or unavailable)"
    fi
else
    echo "    Claude Code CLI not found, skipping plugin update"
fi

# 2. Update global instructions
echo ""
echo "==> Updating global instructions..."
curl -fsSL "$RAE_REPO/$RAE_VERSION/CLAUDE.md" -o .claude/GLOBAL_INSTRUCTIONS.md

# 3. Update guidelines
echo "==> Updating guidelines..."
mkdir -p guidelines
for guide in coding-standards python-standards repo-structure git-workflow anti-patterns; do
    curl -fsSL "$RAE_REPO/$RAE_VERSION/guidelines/${guide}.md" -o "guidelines/${guide}.md"
done

# 4. Update version marker
echo "==> Recording version..."
echo "$RAE_VERSION" > .rae-version

echo ""
echo "╔════════════════════════════════════════════════════════════╗"
echo "║  Sync Complete!                                            ║"
echo "║                                                            ║"
echo "║  Updated from: $CURRENT_VERSION                            ║"
echo "║  Updated to:   $RAE_VERSION                                ║"
echo "║                                                            ║"
echo "║  Changes:                                                  ║"
echo "║  - Claude Code plugin (if installed)                       ║"
echo "║  - .claude/GLOBAL_INSTRUCTIONS.md                          ║"
echo "║  - guidelines/*.md                                         ║"
echo "║  - skills/*/SKILL.md                                       ║"
echo "╚════════════════════════════════════════════════════════════╝"
