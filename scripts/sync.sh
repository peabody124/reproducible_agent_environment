#!/bin/bash
set -euo pipefail

# Reproducible Agent Environment (RAE) Sync Script
# Updates the RAE plugin to the latest version

echo "==> Updating RAE plugin..."
if command -v claude &> /dev/null; then
    if claude plugin update rae@reproducible_agent_environment 2>/dev/null; then
        echo "    ✓ RAE plugin updated"
    else
        echo "    RAE plugin update skipped (not installed or unavailable)"
    fi
else
    echo "    Claude Code CLI not found"
    echo "    Re-run install-user.sh or update manually in Claude Code:"
    echo "      /plugin update rae@reproducible_agent_environment"
fi
