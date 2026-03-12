# Installing Beads for Bead-Driven Development

Beads is **disabled by default** in RAE. Follow these steps to enable it.

## Option 1: Enable in install-user.sh

Uncomment the beads section (step 7) in `scripts/install-user.sh`, then re-run:

```bash
curl -fsSL https://raw.githubusercontent.com/peabody124/reproducible_agent_environment/main/scripts/install-user.sh | bash
```

## Option 2: Manual Installation

### 1. Install beads CLI

```bash
curl -fsSL https://raw.githubusercontent.com/steveyegge/beads/main/scripts/install.sh | bash
export PATH="$HOME/.local/bin:$HOME/go/bin:$PATH"
```

Verify: `bd version`

### 2. Install uv (if not already installed)

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

### 3. Install beads Claude Code plugin

In Claude Code:

```
/plugin marketplace add steveyegge/beads
/plugin install beads@beads-marketplace
```

### 4. Set up Claude Code hooks

```bash
bd setup claude
```

This configures SessionStart and PreCompact hooks for automatic bead syncing.

### 5. Install superpowers plugin

Bead-driven development also requires the superpowers plugin for writing-plans, executing-plans, and investigation skills:

```
/plugin marketplace add obra/superpowers-marketplace
/plugin install superpowers@superpowers-marketplace
```

### 6. Initialize beads in your repo

```bash
bd init
```

## Verifying Installation

```bash
# Check beads CLI
bd version

# Check beads are initialized in repo
bd list

# Check plugins are active (in Claude Code)
/plugin list
```

## Troubleshooting

### git-lfs conflicts

If your project uses `git-lfs`, beads hooks can conflict with LFS hooks. Use:

```bash
git lfs install --force || true
```

### bd command not found

Ensure `$HOME/.local/bin` and `$HOME/go/bin` are on your PATH:

```bash
export PATH="$HOME/.local/bin:$HOME/go/bin:$PATH"
```

Add this to your shell profile (`~/.bashrc` or `~/.zshrc`) for persistence.
