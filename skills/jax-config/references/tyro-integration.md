# Tyro CLI Integration with JAX Pytree Configs

## Overview

[tyro](https://brentyi.github.io/tyro/) is our preferred CLI configuration system.
It generates argument parsers directly from typed dataclasses — no YAML files, no
manual argparse, no schema duplication. This document covers how to use tyro cleanly
with configs that are also registered as JAX pytrees.

## Basic Pattern

```python
# scripts/train.py
import tyro
from my_package.configs import TrainConfig

def main() -> None:
    config = tyro.cli(TrainConfig)
    config.validate()
    train(config)

if __name__ == "__main__":
    main()
```

CLI usage (tyro converts underscores to hyphens automatically):

```bash
python scripts/train.py --learning-rate 3e-4 --model.hidden-dim 256
python scripts/train.py --sampling.lambda-max 50.0 --sampling.n-steps 200
```

## Config Dataclass Conventions

### Docstrings Become Help Text

```python
@dataclass
class ModelConfig:
    """Transformer architecture parameters."""

    hidden_dim: int = 512
    """Hidden dimension of the transformer."""

    num_layers: int = 8
    """Number of transformer layers."""

    num_heads: int = 8
    """Number of attention heads."""

    dropout: float = 0.1
    """Dropout probability."""
```

Each field's docstring (the string literal immediately below the field) becomes
the `--help` text for that argument. Keep them short — one line.

### Nested Configs with `field(default_factory=...)`

```python
@dataclass
class TrainConfig:
    """Complete training configuration."""

    model: ModelConfig = field(default_factory=ModelConfig)
    """Model architecture settings."""

    data: DataConfig = field(default_factory=DataConfig)
    """Dataset and loading settings."""

    sampling: SamplingConfig = field(default_factory=SamplingConfig)
    """Sampling/inference hyperparameters."""

    learning_rate: float = 1e-4
    """Peak learning rate."""

    total_steps: int = 100_000
    """Total training steps."""
```

Tyro creates nested argument groups: `--model.hidden-dim`, `--data.batch-size`, etc.

### Enum Fields

```python
from enum import Enum

class ArchitectureMode(str, Enum):
    pose_only = "pose_only"
    with_scale = "with_scale"
    overcomplete = "overcomplete"

@dataclass
class ModelConfig:
    mode: ArchitectureMode = ArchitectureMode.with_scale
    """Architecture variant to use."""
```

CLI: `--model.mode pose_only` (uses the enum value string).

### Annotated Fields for Special Behavior

```python
from typing import Annotated
import tyro

@dataclass
class CLIConfig:
    # Positional argument (no -- prefix)
    checkpoint: Annotated[str, tyro.conf.Positional]
    """Path to model checkpoint."""

    # Suppress from CLI (always uses default)
    internal_flag: Annotated[bool, tyro.conf.Suppress] = False
```

## The Two-Layer Architecture

Configs play two roles that can conflict:

1. **CLI layer**: Human-friendly defaults, string paths, optional fields
2. **JAX layer**: Pytree-registered, float→array conversion, hashable aux_data

**Recommended approach**: Use the same dataclass for both, with pytree registration
handling the JAX concerns transparently.

```
User types CLI args
        │
        ▼
   tyro.cli(TrainConfig)          ← Pure Python dataclass with defaults
        │
        ▼
   config.validate()              ← Fail-fast checks (outside JIT)
        │
        ▼
   Pass config into jit/filter_jit  ← Pytree registration kicks in:
        │                              float fields → jnp.float32 arrays
        ▼                              int/bool/str → static aux_data
   JAX traces the function
```

The pytree `tree_flatten` function handles the Python-float → JAX-array conversion.
The user never sees JAX arrays in the config; tyro sees plain Python dataclasses.

## Multiple Entry Points

Create separate top-level configs for different scripts. Use inheritance or
composition to share common sub-configs:

```python
@dataclass
class InferenceConfig:
    """Base config for any inference script."""
    model: ModelConfig = field(default_factory=ModelConfig)
    sampling: SamplingConfig = field(default_factory=SamplingConfig)
    checkpoint: str = "checkpoints/best"

@dataclass
class EvalConfig(InferenceConfig):
    """Extends InferenceConfig with evaluation-specific fields."""
    n_samples: int = 1000
    test_data: str | None = None
    metrics: tuple[str, ...] = ("mae", "std")

@dataclass
class SampleConfig(InferenceConfig):
    """Extends InferenceConfig with visualization fields."""
    plot_3d: bool = False
    output_dir: str = "samples"
```

Each script uses its own config:

```python
# scripts/train.py
config = tyro.cli(TrainConfig)

# scripts/eval.py
config = tyro.cli(EvalConfig)

# scripts/sample.py
config = tyro.cli(SampleConfig)
```

## Subcommands with tyro

For scripts that support multiple modes:

```python
from typing import Union
import tyro

@dataclass
class TrainFromScratch:
    """Train a new model from scratch."""
    model: ModelConfig = field(default_factory=ModelConfig)
    total_steps: int = 100_000

@dataclass
class FineTune:
    """Fine-tune from an existing checkpoint."""
    checkpoint: str = "checkpoints/best"
    learning_rate: float = 1e-5
    total_steps: int = 10_000

def main() -> None:
    config = tyro.cli(Union[TrainFromScratch, FineTune])
    if isinstance(config, TrainFromScratch):
        train_from_scratch(config)
    else:
        fine_tune(config)
```

CLI: `python train.py train-from-scratch --total-steps 50000`
CLI: `python train.py fine-tune --checkpoint path/to/ckpt`

## Interaction with Pytree Registration

### Key Consideration: tyro Produces Python Values, Pytree Needs Arrays

When tyro parses `--sampling.lambda-max 50.0`, it produces a Python `float`.
The pytree `tree_flatten` function converts it to `jnp.float32`. This is seamless
— no special handling needed in the tyro layer.

### Serialization Round-Trip

For checkpointing configs alongside model weights:

```python
import json
from dataclasses import asdict

def save_config(config: TrainConfig, path: str) -> None:
    """Save config as JSON for reproducibility."""
    with open(path, "w") as f:
        json.dump(asdict(config), f, indent=2, default=str)

def load_config(path: str) -> TrainConfig:
    """Load config from JSON. Does NOT go through tyro."""
    with open(path) as f:
        d = json.load(f)
    # Reconstruct nested configs manually or use a from_dict classmethod
    return TrainConfig(**d)
```

**Important**: When loading a saved config, you get Python floats, which is fine —
the pytree registration handles the conversion when the config enters JIT.

## Checklist

- [ ] Each script has exactly one `tyro.cli()` call with its specific config type
- [ ] Every field has a one-line docstring (becomes `--help` text)
- [ ] Nested configs use `field(default_factory=...)`, not mutable defaults
- [ ] Enums inherit from `str, Enum` for clean CLI integration
- [ ] `config.validate()` is called after `tyro.cli()`, before any JIT call
- [ ] Pytree registration is in `configs.py`, not in the script
- [ ] Config is JSON-serializable via `dataclasses.asdict()` for reproducibility
