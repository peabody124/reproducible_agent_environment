# Propose Upstream

## Overview

Workflow for proposing configuration, skill, or guideline improvements to the upstream Reproducible Agent Environment (RAE) repository.

## Trigger

Agent discovers a better pattern during work:
- Improved pytest/ruff configuration
- New or refined guideline
- Enhanced skill
- Better default settings

## Steps

### 1. Evaluate Scope

Determine if the improvement is universal or project-specific.

**Constraints:**
- You MUST verify the improvement works in the current project first
- You MUST check if a similar pattern already exists upstream
- You SHOULD consider if this applies to most Python projects or is domain-specific

**Decision Tree:**
```
Is this useful for most projects?
├── YES → Continue to step 2
└── NO → Add to project's local overrides with comment, STOP
```

### 2. Check Upstream State

Before creating changes, understand current upstream.

**Constraints:**
- You MUST pull latest from upstream RAE repository
- You SHOULD check open PRs for similar improvements
- You MUST NOT duplicate existing functionality

### 3. Branch and Implement

Create the improvement in a clean branch.

**Constraints:**
- You MUST use descriptive branch name: `improve/<area>-<change>`
  - Examples: `improve/ruff-async-rules`, `guideline/error-handling`
- You MUST make atomic commits with clear messages
- You SHOULD include before/after examples in commit body

### 4. Create Pull Request

Open PR with complete context.

**Constraints:**
- You MUST include:
  - Summary of the improvement (1-3 sentences)
  - Rationale (why is this better?)
  - Before/after examples if applicable
  - Any potential breaking changes
- You SHOULD reference the project where this was discovered
- You MUST NOT include project-specific details

### 5. Update Local After Merge

Once the PR is merged:

**Constraints:**
- You MUST update the RAE plugin (`/plugin update rae@reproducible_agent_environment`) to pull the improvement
- You MUST verify the improvement works correctly
- You SHOULD remove any local overrides that are now upstream

## Examples

**Scenario:** Discovered that adding `RUF` rules to ruff catches more issues.

1. Verify it works locally ✓
2. Check upstream templates/pyproject.toml - not present ✓
3. Create branch `improve/ruff-ruf-rules`
4. Update pyproject.toml, commit with rationale
5. Open PR: "Add RUF rules to ruff config for additional checks"
6. After merge: update the RAE plugin and remove local override

## Troubleshooting

**PR conflicts:** Rebase on latest main, resolve conflicts, force push to branch.

**Improvement rejected:** Add rationale to local override explaining why you use it anyway.
