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
- OpenCV dependencies (libgl1, libglib2.0-0)
- Git LFS for large model files
- Jupyter notebook support
- Project auto-install: `pip install -e '.[dev]'`
- Claude Code auto-install via `postCreateCommand`

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

> **Note:** The default `.env.template` sets `CUDA_VISIBLE_DEVICES=-1` (no GPU).
> You must assign a specific GPU (e.g. `CUDA_VISIBLE_DEVICES=0`) before running
> any GPU workload. Use `nvidia-smi` on the host to see available devices.

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
