# RAE Project Templates

This directory contains templates for scaffolding new Python projects with RAE standards.

## Files

| File | Purpose |
|------|---------|
| `.gitignore` | Standard Python gitignore with RAE patterns |
| `pyproject.toml` | Base pyproject.toml structure (used by scaffold-repo) |
| `devcontainer-cpu/` | Lightweight CPU-only devcontainer |
| `devcontainer-gpu/` | Full GPU devcontainer with CUDA + cuDNN |

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
- GPU access via `--gpus all`
- OpenCV / headless rendering dependencies (`libgl1`, `libegl1`, `libglib2.0-0`)
- Git LFS for large model files
- Jupyter notebook support
- Project auto-install: `pip install -e '.[dev]'`
- Claude Code auto-install via `postCreateCommand`

If a project renders with PyOpenGL in headless mode (`PYOPENGL_PLATFORM=egl`), keep `libegl1` in the devcontainer so `libEGL.so.1` is available.

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
