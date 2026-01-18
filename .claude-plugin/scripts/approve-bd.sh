#!/bin/bash
# Auto-approve beads (bd) commands for bead-driven-development skill
# This hook runs before Bash tool execution

# Read the tool input from stdin
input=$(cat)
command=$(echo "$input" | jq -r '.tool_input.command // empty')

# Auto-approve bd commands
if [[ "$command" =~ ^bd[[:space:]] ]] || [[ "$command" == "bd" ]]; then
  # Return allow decision
  echo '{"decision": "allow"}' >&2
  exit 0
fi

# Let other commands go through normal approval flow
exit 0
