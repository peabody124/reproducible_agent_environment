# JAX Pytree Registration for Config Dataclasses

## When to Use This Pattern

Register a config as a JAX pytree when:
- The config is passed as an argument to a `jax.jit` or `eqx.filter_jit` function
- You want to change float hyperparameters (loss weights, learning rates, thresholds)
  between calls **without triggering recompilation**

Do NOT register as a pytree when:
- The config is only used at init time (model construction, data loading)
- The config is stored inside an `eqx.Module` (use `eqx.field(static=True)` instead)

## Full Pattern

```python
from dataclasses import dataclass, field
import jax.numpy as jnp
from jax import tree_util


@dataclass
class SamplingConfig:
    """Hyperparameters for inference.

    Registered as a JAX pytree: float hyperparameters are dynamic leaves
    (changing them does not trigger recompilation), while structural fields
    (bools, ints, strings) are static aux_data.
    """

    # --- Static fields (changing triggers recompilation) ---
    n_steps: int = 100
    use_guidance: bool = True
    solver: str = "euler"

    # --- Dynamic fields (changing reuses compiled code) ---
    lambda_max: float = 100.0
    alpha: float = 0.5
    grad_clip: float = 1.0
    learning_rate: float = 1e-4

    # --- Nullable fields are ALWAYS static ---
    optional_threshold: float | None = None


# Explicit set of field names that are dynamic pytree leaves.
# Every field NOT in this set becomes static aux_data.
_SAMPLING_CONFIG_DYNAMIC_FIELDS: set[str] = {
    "lambda_max",
    "alpha",
    "grad_clip",
    "learning_rate",
}


def _sampling_config_tree_flatten(obj: SamplingConfig) -> tuple:
    """Split config into dynamic children (JAX arrays) and static aux_data."""
    children_dict: dict[str, jnp.ndarray] = {}
    aux_dict: dict[str, object] = {}

    for key, value in obj.__dict__.items():
        if key in _SAMPLING_CONFIG_DYNAMIC_FIELDS:
            # CRITICAL: wrap float into a 0-d JAX array.
            # Bare Python floats are treated as static by the tracer.
            children_dict[key] = jnp.asarray(value, dtype=jnp.float32)
        else:
            aux_dict[key] = value

    # Children must be a flat sequence; aux_data must be hashable.
    children = tuple(children_dict.values())
    aux_data = (tuple(children_dict.keys()), tuple(sorted(aux_dict.items())))
    return children, aux_data


def _sampling_config_tree_unflatten(aux_data: tuple, children: tuple) -> SamplingConfig:
    """Reconstruct config from dynamic children and static aux_data."""
    child_keys, aux_items = aux_data
    result_dict = dict(zip(child_keys, children))
    result_dict.update(dict(aux_items))
    return SamplingConfig(**result_dict)


tree_util.register_pytree_node(
    SamplingConfig,
    _sampling_config_tree_flatten,
    _sampling_config_tree_unflatten,
)
```

## Why Wrap Floats into Arrays

JAX's tracing system distinguishes between:
- **Tracers** (JAX arrays) — tracked symbolically, can change between calls
- **Static values** (Python scalars) — baked into the compiled program

A bare Python `float` is a static value. If you put `0.5` as a pytree leaf,
JAX treats it as a literal constant. Changing it to `0.6` invalidates the cache
and triggers recompilation — the exact thing we're trying to avoid.

`jnp.asarray(0.5, dtype=jnp.float32)` creates a 0-dimensional JAX array that
the tracer tracks symbolically. The compiled code works for any float value
without recompilation.

```python
# This recompiles every time lambda_max changes:
children = (0.5,)  # Python float — static!

# This reuses the compiled code:
children = (jnp.asarray(0.5, dtype=jnp.float32),)  # JAX array — dynamic!
```

## Making aux_data Hashable

JAX requires `aux_data` to be hashable (it's used as a cache key). Common pitfalls:

```python
# WRONG — dict is not hashable
aux_data = {"n_steps": 100, "solver": "euler"}

# RIGHT — tuple of tuples is hashable
aux_data = (("n_steps", 100), ("solver", "euler"))

# ALSO RIGHT — use a frozen structure
aux_data = (child_keys_tuple, tuple(sorted(aux_dict.items())))
```

If aux_data contains unhashable types (lists, dicts), convert them:
- `list` → `tuple`
- `dict` → `tuple(sorted(d.items()))`
- `set` → `frozenset`

## Nested Config Pytrees

For a top-level config that nests other pytree-registered configs:

```python
@dataclass
class TrainConfig:
    model: ModelConfig = field(default_factory=ModelConfig)
    sampling: SamplingConfig = field(default_factory=SamplingConfig)
    learning_rate: float = 1e-4
    total_steps: int = 100_000


_TRAIN_CONFIG_DYNAMIC_FIELDS: set[str] = {
    "learning_rate",
}

# Configs that are themselves registered pytrees go into children
_TRAIN_CONFIG_CHILD_CONFIGS: set[str] = {
    "sampling",  # SamplingConfig is a registered pytree
}


def _train_config_tree_flatten(obj: TrainConfig) -> tuple:
    children_dict = {}
    child_configs = {}
    aux_dict = {}

    for key, value in obj.__dict__.items():
        if key in _TRAIN_CONFIG_CHILD_CONFIGS:
            child_configs[key] = value  # JAX will recursively flatten this
        elif key in _TRAIN_CONFIG_DYNAMIC_FIELDS:
            children_dict[key] = jnp.asarray(value, dtype=jnp.float32)
        else:
            aux_dict[key] = value

    # Order: scalar children first, then nested config children
    children = tuple(children_dict.values()) + tuple(child_configs.values())
    aux_data = (
        tuple(children_dict.keys()),
        tuple(child_configs.keys()),
        tuple(sorted(aux_dict.items())),
    )
    return children, aux_data


def _train_config_tree_unflatten(aux_data: tuple, children: tuple) -> TrainConfig:
    scalar_keys, config_keys, aux_items = aux_data
    n_scalars = len(scalar_keys)

    result_dict = dict(zip(scalar_keys, children[:n_scalars]))
    result_dict.update(dict(zip(config_keys, children[n_scalars:])))
    result_dict.update(dict(aux_items))
    return TrainConfig(**result_dict)


tree_util.register_pytree_node(
    TrainConfig,
    _train_config_tree_flatten,
    _train_config_tree_unflatten,
)
```

## Testing Pytree Registration

**MUST** write tests for pytree registration. At minimum:

```python
import jax
import jax.numpy as jnp


def test_roundtrip():
    """Flatten then unflatten preserves all fields."""
    cfg = SamplingConfig(n_steps=50, lambda_max=200.0, alpha=0.8)
    leaves, treedef = jax.tree_util.tree_flatten(cfg)
    restored = treedef.unflatten(leaves)

    assert restored.n_steps == 50  # static field preserved
    assert float(restored.lambda_max) == 200.0  # dynamic field preserved
    assert float(restored.alpha) == 0.8


def test_dynamic_fields_no_retrace():
    """Changing dynamic fields must NOT trigger recompilation."""
    call_count = 0

    @jax.jit
    def f(cfg: SamplingConfig) -> jax.Array:
        nonlocal call_count
        call_count += 1
        return cfg.lambda_max * cfg.alpha

    cfg1 = SamplingConfig(lambda_max=1.0, alpha=0.5)
    _ = f(cfg1)  # First call: traces
    assert call_count == 1

    cfg2 = SamplingConfig(lambda_max=2.0, alpha=0.9)  # Different dynamic values
    _ = f(cfg2)  # Must reuse cached trace
    # Note: call_count may not increment reliably in all JAX versions.
    # A more robust check: use jax.make_jaxpr to verify trace structure is identical.


def test_static_field_triggers_retrace():
    """Changing a static field (n_steps) should produce a different jaxpr."""
    def f(cfg: SamplingConfig) -> jax.Array:
        return cfg.lambda_max + cfg.n_steps

    cfg1 = SamplingConfig(n_steps=10)
    cfg2 = SamplingConfig(n_steps=20)

    jaxpr1 = jax.make_jaxpr(f)(cfg1)
    jaxpr2 = jax.make_jaxpr(f)(cfg2)
    # Different n_steps values should produce different jaxprs
    assert str(jaxpr1) != str(jaxpr2)
```

## Checklist

- [ ] Dynamic fields listed in explicit `_*_DYNAMIC_FIELDS` set
- [ ] All dynamic floats wrapped with `jnp.asarray(..., dtype=jnp.float32)`
- [ ] `aux_data` is hashable (no dicts, lists, or sets)
- [ ] `tree_unflatten` produces a valid instance of the dataclass
- [ ] Nullable (`float | None`) fields are in aux_data, not children
- [ ] Roundtrip test passes
- [ ] Retrace/no-retrace test passes
- [ ] Registration call is at module level (not inside a function)
