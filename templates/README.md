# RAE Project Templates

This directory contains templates for scaffolding new Python projects with RAE standards.

## Files

| File | Purpose |
|------|---------|
| `.gitignore` | Standard Python gitignore with RAE patterns |
| `pyproject.toml` | Base pyproject.toml structure (used by scaffold-repo) |
| `devcontainer-cpu/` | Lightweight CPU-only devcontainer |
| `devcontainer-gpu/` | Full GPU devcontainer with CUDA + cuDNN |
| `myst-paper/` | Canonical MyST Markdown paper scaffold with dual ISR (`templates/isr`) and IEEE (`templates/ieeetrans`) builds, `build_isr.sh`, `build_ieee.sh`, `BUILD.md`, and `scripts/diff_commits_pdf.py` |

## Devcontainer Templates

### CPU-only (devcontainer-cpu/)

**Use for:** Web apps, APIs, general Python development

**Features:**
- Base image: `mcr.microsoft.com/devcontainers/python:3.11`
- Lightweight and fast startup
- Claude Code auto-install via `postCreateCommand`
- VSCode configured with ruff, Python tools

**Setup:**
```bash
mkdir -p .devcontainer
cp templates/devcontainer-cpu/devcontainer.json .devcontainer/
mkdir -p ~/.claude  # On host machine
```

### GPU-enabled (devcontainer-gpu/)

**Use for:** Machine learning, computer vision, biomechanics, pose estimation

**Features:**
- Base image: `nvidia/cuda:12.6.0-cudnn-devel-ubuntu24.04`
- GPU access via `--gpus all` with `-e NVIDIA_DRIVER_CAPABILITIES=compute,utility,graphics`
- OpenCV, EGL, and Vulkan rendering dependencies (`libgl1`, `libegl1`, `libvulkan1`, `libglib2.0-0`, `libosmesa6-dev`) plus NVIDIA GLVND (`10_nvidia.json`) and Vulkan (`nvidia_icd.json`) ICD manifests
- Git LFS for large model files
- Jupyter notebook support
- Project auto-install: `pip install -e '.[dev]'`
- Claude Code auto-install via `postCreateCommand`

### Headless GPU Rendering (EGL, OpenGL & Vulkan / Isaac Sim / MuJoCo / pyrender)

Because `nvidia/cuda` base images set `NVIDIA_DRIVER_CAPABILITIES=compute,utility` by default and do not ship GLVND/Vulkan JSON manifests, three things are required in `devcontainer.json` for hardware rendering:

1. **Enable `graphics` driver capabilities at container creation:** Pass `"-e", "NVIDIA_DRIVER_CAPABILITIES=compute,utility,graphics"` in `runArgs` (and in `containerEnv`) so `nvidia-container-cli` mounts `libEGL_nvidia.so.0`, `libGLX_nvidia.so.0`, `libnvidia-rtcore.so`, and `libnvidia-glvkspirv.so`.
2. **Register NVIDIA EGL & Vulkan ICD manifests in `onCreateCommand`:** Installing `libgl1 libegl1 libvulkan1` on Ubuntu 24.04 only writes `/usr/share/glvnd/egl_vendor.d/50_mesa.json` and `/usr/share/vulkan/icd.d/lvp_icd.json`. Without `/usr/share/glvnd/egl_vendor.d/10_nvidia.json` (`libEGL_nvidia.so.0`) and `/etc/vulkan/icd.d/nvidia_icd.json` (`libGLX_nvidia.so.0`), EGL fails with `EGL_NOT_INITIALIZED` or silently falls back to CPU `llvmpipe` (10–50× slower), and Vulkan cannot find the NVIDIA driver. Both manifests are automatically written by the GPU template's `onCreateCommand`.
3. **Include `/dev/nvidia-modeset` and `/dev/dri` when manually filtering GPU devices:** If a host has unhealthy GPUs and you manually pass `--device=/dev/nvidia0`, `--device=/dev/nvidiactl`, `--device=/dev/nvidia-uvm` in `runArgs`, you **must also include `--device=/dev/nvidia-modeset` and `--device=/dev/dri`**. Without them, CUDA and EGL pbuffers still work, but Vulkan/RTX renderers (Isaac Sim `omni.rtx`, SAPIEN, ManiSkill, `vkCreateDevice`) fail or segfault on device creation.

See the **`/efficient-rendering`** skill for runtime GPU probing, `llvmpipe` assertions, context reuse, and camera conventions.

**Setup:**
```bash
mkdir -p .devcontainer
cp templates/devcontainer-gpu/devcontainer.json .devcontainer/
mkdir -p ~/.claude  # On host machine
touch .env          # Create env file for secrets
```

**GPU template requires `.env` file:**
```bash
# .env (add to .gitignore!)
# GPU selection — no GPU by default so containers don't grab GPUs unexpectedly.
# CUDA_DEVICE_ORDER=PCI_BUS_ID ensures device IDs match nvidia-smi output.
# Change CUDA_VISIBLE_DEVICES to a GPU index (e.g. 0) when ready to use one.
CUDA_DEVICE_ORDER=PCI_BUS_ID
CUDA_VISIBLE_DEVICES=-1

# Add secrets here as needed:
# HUGGINGFACE_TOKEN=hf_...
# WANDB_API_KEY=...
```

> **Note:** Both devcontainer templates default to `CUDA_VISIBLE_DEVICES=-1` (no GPU).
> Before running any GPU workload, use `nvidia-smi` to find a free GPU and explicitly
> set one: `export CUDA_VISIBLE_DEVICES=0`. Never use all GPUs without checking first.

### GPU Selection for Agents

Add this to your project's `CLAUDE.md` so agents select GPUs responsibly:

```markdown
## GPU Usage
Before running any GPU workload, run `nvidia-smi` to find a free GPU
(look for one with low memory usage and no running processes). Then set:
```bash
export CUDA_VISIBLE_DEVICES=<gpu_id>   # e.g. 0, 1, etc.
```
Never use multiple GPUs without explicit permission. Never leave
CUDA_VISIBLE_DEVICES unset — the default is -1 (no GPU) for safety.
```

## Using with /scaffold-repo

The `/scaffold-repo` skill automatically offers both templates when creating a new project:

```
/scaffold-repo my-project "A tool for pose estimation"
```

The skill will ask which devcontainer template you want (CPU or GPU).

## Manual Template Usage

Without using `/scaffold-repo`, you can manually copy templates:

```bash
# Copy base files
cp templates/.gitignore .
cp templates/pyproject.toml .

# Choose devcontainer
cp -r templates/devcontainer-cpu/.devcontainer .
# OR
cp -r templates/devcontainer-gpu/.devcontainer .
```

Then customize `pyproject.toml` with your project name and dependencies.
