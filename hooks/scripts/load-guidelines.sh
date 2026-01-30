#!/bin/bash
set -euo pipefail

# Load RAE guidelines into Claude Code session context.
# Called by SessionStart hook to ensure guidelines are always available.

PLUGIN_ROOT="${CLAUDE_PLUGIN_ROOT:-$(dirname "$(dirname "$(dirname "$0")")")}"
REF_DIR="$PLUGIN_ROOT/skills/enforce-guidelines/references"

if [ ! -d "$REF_DIR" ]; then
    echo "RAE guidelines not found at $REF_DIR" >&2
    exit 0
fi

echo "# RAE Guidelines (auto-loaded)"
echo ""

# Load the core guidelines that apply to every session.
# repo-structure.md is excluded — only relevant when scaffolding new repos.
for guide in coding-standards python-standards git-workflow anti-patterns pre-commit-checklist; do
    file="$REF_DIR/${guide}.md"
    if [ -f "$file" ]; then
        cat "$file"
        echo ""
        echo "---"
        echo ""
    fi
done
