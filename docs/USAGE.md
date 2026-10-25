# Reproducible Agent Environment (RAE) - Usage Guide

## Overview

RAE provides standardized AI agent configurations across projects. It supports Claude Code with shared skills, coding standards, and a SessionStart hook that auto-loads guidelines.

For installation, see the [README](../README.md).

## Local Overrides

Add project-specific instructions to `CLAUDE.md`:

```markdown
# Project Agent Instructions

## Project Context

This project is a biomechanics analysis tool using JAX...

## Project-Specific Commands

- `make analyze` — Run motion capture analysis
- `make report` — Generate PDF report

## Local Overrides

<!-- Override: Using dict.get for external API responses -->
For this project, we allow dict.get when parsing external API responses
because the schema is not guaranteed.
```

## Available Skills

Skills are available through the Claude Code plugin:

### Core Skills

| Skill | Description |
|-------|-------------|
| `/enforce-guidelines` | Ensures work follows RAE standards (auto-activates) |
| `/deslop` | Clean AI-generated slop from staged changes |
| `/consult-guidelines` | Review relevant guidelines for current task |
| `/scaffold-repo` | Create new repos with correct structure |
| `/config-improvement` | Propose improvements to upstream RAE |
| `/bead-driven-development` | Orchestrate planning + execution with beads tracking (optional, disabled by default) |
| `/investigation` | Scaffold structured research in scratch/ |

### Domain-Specific Skills

| Skill | Description |
|-------|-------------|
| `/datajoint-biomechanics-schema` | DataJoint pipeline schema reference |
| `/pose-datajoint` | Python code patterns for DataJoint pose queries |
| `/gait-metrics` | Gait analysis: walking segments, spatiotemporal metrics, GDI |

## Proposing Improvements

When you discover a better pattern:

1. Verify it works in your project
2. Check if it's universal or project-specific
3. If universal, use `/config-improvement` or manually create a PR
4. After merge, update the RAE plugin to get the improvement

## Troubleshooting

### Skills not loading

1. Check plugin is installed: `/plugin list`
2. Re-install the plugin if needed
3. Restart Claude Code session

### `git lfs install` fails in devcontainer with exit code 2

If your `onCreateCommand` includes `git lfs install` and the repo has beads git hooks enabled (or other custom hooks), `git lfs install` will refuse to overwrite them and exit non-zero. This silently aborts the entire `onCreateCommand` chain, preventing `postCreateCommand` from ever running — making the container appear to hang.

**Fix:** Use `git lfs install --force || true` instead of `git lfs install`:

```jsonc
"onCreateCommand": "sudo apt-get update && sudo apt-get install -y ... git-lfs && sudo rm -rf /var/lib/apt/lists/* && (git lfs install --force || true)"
```

`--force` overwrites conflicting hooks, and `|| true` ensures the build continues even if git-lfs setup fails for other reasons.

### Headless GPU rendering (EGL & Vulkan) in NVIDIA devcontainers

`nvidia/cuda:*-ubuntu24.04` images default to `NVIDIA_DRIVER_CAPABILITIES=compute,utility` and do not ship GLVND or Vulkan ICD JSON manifests. Installing `libgl1 libegl1 libvulkan1` via `apt` only installs Mesa's `50_mesa.json` and `lvp_icd.json`, causing PyOpenGL/pyrender/MuJoCo to fail with `EGL_NOT_INITIALIZED` or fall back to CPU `llvmpipe`, and causing Vulkan renderers (Isaac Sim, SAPIEN, ManiSkill) to miss the NVIDIA GPU.

**Fix:** Ensure your `.devcontainer/devcontainer.json` includes:

1. **`graphics` driver capability in `runArgs` and `containerEnv`:**
   ```jsonc
   "runArgs": [
     "--env-file", ".env",
     "--gpus", "all",
     "-e", "NVIDIA_DRIVER_CAPABILITIES=compute,utility,graphics"
   ],
   "containerEnv": {
     "NVIDIA_DRIVER_CAPABILITIES": "compute,utility,graphics",
     "PYOPENGL_PLATFORM": "egl",
     "MUJOCO_GL": "egl"
   }
   ```
2. **NVIDIA EGL & Vulkan ICD manifests in `onCreateCommand`:**
   ```jsonc
   "onCreateCommand": "sudo apt-get update && sudo apt-get install -y libgl1 libegl1 libvulkan1 libglib2.0-0 libosmesa6-dev git-lfs && sudo mkdir -p /usr/share/glvnd/egl_vendor.d /etc/vulkan/icd.d && printf '{\"file_format_version\":\"1.0.0\",\"ICD\":{\"library_path\":\"libEGL_nvidia.so.0\"}}\\n' | sudo tee /usr/share/glvnd/egl_vendor.d/10_nvidia.json >/dev/null && printf '{\"file_format_version\":\"1.0.0\",\"ICD\":{\"library_path\":\"libGLX_nvidia.so.0\",\"api_version\":\"1.3\"}}\\n' | sudo tee /etc/vulkan/icd.d/nvidia_icd.json >/dev/null && sudo rm -rf /var/lib/apt/lists/* && (git lfs install --force || true)"
   ```
3. **DRM & modeset devices when manually filtering GPUs:** If you pass explicit `--device=/dev/nvidia0` flags in `runArgs` (e.g., to isolate healthy GPUs on a multi-GPU server), you **must also include `--device=/dev/nvidia-modeset` and `--device=/dev/dri`**, or Vulkan `vkCreateDevice` / Isaac Sim `omni.rtx` will segfault or fail with `No device could be created`.
