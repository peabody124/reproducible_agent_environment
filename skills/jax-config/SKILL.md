---
name: jax-config
description: >
  Set up JAX/Equinox-compatible configuration for a project. Use when the user says
  "set up config", "add configuration", "make a config", "jax config", or when creating
  dataclass configs that will be passed through JAX-traced code. Also use when debugging
  recompilation issues or pytree registration problems.
---

# JAX-Compatible Configuration

## Overview

This skill sets up typed configuration dataclasses that work cleanly with JAX tracing,
Equinox modules, and tyro CLI parsing. The core challenge: JAX's `jit` traces code and
caches compiled versions keyed on the **static** components of its inputs. Configs must
cleanly separate dynamic values (JAX array leaves that can change without recompilation)
from static values (Python values baked into the trace).

Refer to `references/pytree-registration.md` for the full pytree registration pattern
and `references/tyro-integration.md` for CLI configuration with tyro.

## Decision Flow

1. **Will this config be passed into a `jit`/`filter_jit` function?**
   - YES → Register it as a JAX pytree (see references/pytree-registration.md)
   - NO → Plain `@dataclass` is fine

2. **Is the config part of an `eqx.Module` (model, layer, etc.)?**
   - YES → Use `eqx.field(static=True)` on structural fields
   - NO → Use pytree registration with explicit dynamic/static field sets

3. **Does the config need CLI parsing?**
   - YES → Use tyro (see references/tyro-integration.md)
   - NO → Plain `@dataclass` with defaults

## The Golden Rules

### Rule 1: Separate Static from Dynamic

**Static fields** (changing them SHOULD trigger recompilation):
- `int` — loop bounds, array shapes, sequence lengths
- `bool` — control flow switches
- `str` — mode selectors, paths
- `Enum` — architecture variants
- `None | float` — nullable fields (structural change)

**Dynamic fields** (changing them MUST NOT trigger recompilation):
- `float` — loss weights, learning rates, thresholds, hyperparameters
- Anything used in pure arithmetic, not control flow

### Rule 2: Wrap Scalar Floats into Arrays

**CRITICAL**: JAX does not properly trace bare Python `float` values as dynamic
pytree leaves. A bare `float` in a pytree leaf position gets treated as a static
value by the tracer, defeating the purpose of making it dynamic.

```python
# WRONG — bare float stays static, recompiles on every change
children_dict[key] = value  # value is 0.5 (Python float)

# RIGHT — wrapped into a 0-d array, properly traced as dynamic
children_dict[key] = jnp.asarray(value, dtype=jnp.float32)
```

Always convert dynamic float fields to `jnp.float32` arrays in the `tree_flatten`
function. The `tree_unflatten` function receives JAX arrays and can pass them
directly to the dataclass constructor (they behave like floats in arithmetic).

### Rule 3: Validate Outside JIT

Config validation (range checks, incompatible option detection) MUST happen at
startup, never inside a traced function. Call `config.validate()` once before
entering any JIT boundary.

```python
config = tyro.cli(MyConfig)
config.validate()  # Fail fast here, not inside jit
train(model, config)  # Now safe to pass into traced code
```

## Quick Reference: Field Classification

| Field Type | Static/Dynamic | Why |
|-----------|---------------|-----|
| `int` | Static | Often controls loops or shapes |
| `bool` | Static | Controls `if` branches in trace |
| `str` | Static | Mode selection, paths |
| `Enum` | Static | Architecture variants |
| `float` | **Dynamic** | Hyperparameters, weights, thresholds |
| `float \| None` | **Static** | Nullability is structural |
| `tuple[float, ...]` | Static | Length is structural |
| `jax.Array` | **Dynamic** | Already a JAX type |

## Equinox Module Config Fields

When config values live inside an `eqx.Module`, use `eqx.field(static=True)`:

```python
class MyModel(eqx.Module):
    # Dynamic — learnable parameters (JAX arrays)
    encoder: eqx.nn.Linear
    decoder: eqx.nn.Linear

    # Static — architecture config (baked into trace)
    hidden_dim: int = eqx.field(static=True)
    num_layers: int = eqx.field(static=True)
    mode: ArchitectureMode = eqx.field(static=True)
    dropout_rate: float = eqx.field(static=True)  # Static if used in control flow
```

**Note:** In `eqx.Module`, even `float` fields that control dropout probability or
similar structural behavior should be `static=True`. The dynamic-float rule applies
to **pytree-registered dataclasses** where you explicitly want to tune hyperparameters
without recompilation.

## Common Mistakes

| Mistake | Fix |
|---------|-----|
| Passing a plain `@dataclass` config into `jit` | Register it as a pytree or make it an `eqx.Module` |
| Bare `float` as pytree leaf | Wrap with `jnp.asarray(value, dtype=jnp.float32)` in `tree_flatten` |
| Validating config inside `jit` | Move validation to startup, before any traced calls |
| Using `eqx.field(static=True)` on a float you want to sweep | Remove `static=True`; or use pytree registration instead |
| Changing an `int` field and expecting no recompilation | Ints are always static — this is correct behavior |
| `float \| None` as dynamic field | Keep it static — `None` vs `float` is a structural change |
| Not testing retrace behavior | Write a test that changes dynamic fields and asserts no retrace |

## File Organization

```
src/my_package/
├── configs.py          # All config dataclasses + pytree registration
├── model.py            # eqx.Module with eqx.field(static=True)
└── train.py            # tyro.cli() entry point
scripts/
├── train.py            # tyro.cli(TrainConfig)
├── eval.py             # tyro.cli(EvalConfig)
└── sample.py           # tyro.cli(SampleConfig)
```

Keep all configs in a single `configs.py`. Pytree registration goes at the bottom
of the same file, immediately after the dataclass definitions.

## References

- `references/pytree-registration.md` — Full pattern for registering configs as JAX pytrees
- `references/tyro-integration.md` — CLI configuration with tyro + JAX pytree configs
- `enforce-guidelines/references/python-standards.md` — Python coding standards
- `enforce-guidelines/references/coding-standards.md` — TDD, fail-fast
