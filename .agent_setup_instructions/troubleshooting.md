# RAE Troubleshooting

Common issues and solutions for RAE installation and usage.

## Plugin Installation Issues

### "Marketplace not found"

**Symptom:** `/plugin marketplace add` fails

**Solution:**
1. Check the repository URL is correct: `peabody124/reproducible_agent_environment`
2. Verify network connectivity
3. Try with full HTTPS URL if shorthand fails

### "Plugin install failed"

**Symptom:** Marketplace added but plugin won't install

**Solution:**
1. Check plugin name: `rae@reproducible_agent_environment`
2. Update Claude Code to latest version
3. Try removing and re-adding the marketplace

## Skill Issues

### Skills not appearing in /help

**Symptom:** RAE skills don't show up

**Solution:**
1. Restart Claude Code session
2. Verify plugin is installed: `/plugin list`
3. Re-install the plugin

### "Guideline not found"

**Symptom:** Skills can't access guidelines

**Solution:**
1. Check if `guidelines/` exists in current project
2. If not, skills should fall back to plugin bundle
3. Run bootstrap.sh to create local guidelines if needed

## Dev Container Issues

### RAE not available in container

**Symptom:** Fresh container doesn't have RAE

**Solution:**
1. Check `postCreateCommand` in devcontainer.json
2. Should run: `curl -fsSL .../scripts/install-user.sh | bash`
3. Manually run `install-user.sh` if needed

### Credentials not mounted

**Symptom:** Can't authenticate to install plugins

**Solution:**
1. Check devcontainer.json mounts include `~/.claude`
2. Verify `CLAUDE_CONFIG_DIR` is set in containerEnv
3. Verify credentials exist on host machine
4. Restart container after adding mounts

## Common Errors

### "Permission denied"

**Cause:** Trying to write to protected directory

**Solution:**
1. Ensure ~/.claude/ is writable
2. Check user permissions in container

### "Network error"

**Cause:** Can't reach GitHub to fetch plugin

**Solution:**
1. Check internet connectivity
2. Try again with retry
3. Use local installation if network unreliable

## Getting Help

If issues persist:

1. Check RAE repository issues: https://github.com/peabody124/reproducible_agent_environment/issues
2. Use `/config-improvement` skill to report the issue
3. Provide: Claude Code version, error message, steps to reproduce
