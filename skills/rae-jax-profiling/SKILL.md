---
name: rae-jax-profiling
description: Canonical RAE standard for JAX/Equinox JIT compilation hygiene, zero-recompilation verification, memory/fusion optimization, and cold-vs-warm profiling across eqx_pose repositories. Use when implementing new JAX/Equinox algorithms, optimizing heavy biomechanics/kinematics/vision loops, fixing JIT retracing or closure cache misses, bucket-padding variable-length sequences T, replacing Python training loops with lax.scan, or benchmarking cold compile vs. warm block_until_ready step latency.
---

# RAE JAX Recompilation & Profiling Skill (`rae-jax-profiling`)

This skill consolidates the canonical Reproducible Agent Environment (RAE) standards from `jax-jit-and-fusion`, `jax-memory-and-retracing`, and `jax-config` into a single operational checklist and verification protocol for `/workspaces/eqx_pose`.

Any newly implemented or compute-heavy JAX/Equinox algorithm **must** satisfy the 7 rules below and pass both a **single-compile assertion test** (`max_traces=1`) and a **cold-vs-warm `jax.block_until_ready()` benchmark**.

---

## 1. `eqx.filter_jit` & PyTree Dynamic vs. Static Separation

1. **Always decorate entry points with `@eqx.filter_jit`**, never bare `@jax.jit`, when arguments include `eqx.Module` instances, callable PyTrees, or dataclass configs. `eqx.filter_jit` automatically partitions all JAX arrays (`eqx.is_array`) as dynamic traced leaves and treats non-array metadata as static.
2. **Pass scalar hyperparameters/weights that vary across calls as traced `jnp.float32` / `jnp.int32` arrays** (or register config dataclasses via `@register_config_dataclass` where varying weights are `Array` fields). Python `float`, `int`, and `bool` values are hashed statically by `eqx.filter_jit` — varying them across trials or ablation toggles (e.g., `use_sensors=True` vs `False`) triggers a full XLA recompilation unless converted to traced `jnp.float32` multipliers (`0.0` vs `1.0`).
3. **Never bake large frozen model weights as XLA constants inside closures.** If a stage optimizer uses `jax.jit` over a flat parameter vector `theta`, split the frozen model via `model_arrays, model_static = eqx.partition(model, eqx.is_array)`, pass `model_arrays` in the traced `data` dict, and reconstruct `model = eqx.combine(data["model_arrays"], model_static)` inside the traced function.
4. **Keep biomechanical/kinematic arrays in `jnp.float32`** throughout `eqx_pose` pipelines.

---

## 2. Bucket-Padding Variable Sequence Lengths $T$ with Masks

Because XLA compiles a distinct executable for every unique tensor shape, passing raw trial lengths $T \in \{187, 243, 312, \dots\}$ to a jitted solver or trajectory fitter causes an $O(\text{num\_trials})$ compilation storm and host/GPU OOM.

1. **Snap $T$ to a small geometric bucket set** (e.g., `BUCKETS = (64, 128, 256, 512, 1024, 2048)`):
   ```python
   def bucket_length(n: int, buckets: tuple[int, ...] = (64, 128, 256, 512, 1024, 2048)) -> int:
       for b in buckets:
           if b >= n:
               return b
       return ((n + buckets[-1] - 1) // buckets[-1]) * buckets[-1]
   ```
2. **Edge-pad time/observation arrays to $T_{\text{bucket}}$ and attach a float32 validity mask `mask` of shape `(T_bucket,)`** (`1.0` for valid frames $0 \le t < T$, `0.0` for padded tail frames $T \le t < T_{\text{bucket}}$):
   - Use `mode="edge"` when padding timestamps and poses so finite differences / Nadaraya-Watson kernels / Jacobians remain well-conditioned on padded rows.
   - Replace `jnp.mean(err)` with masked reductions:
     ```python
     def masked_mean(values: Array, mask: Array) -> Array:
         w = jnp.reshape(mask, (mask.shape[0],) + (1,) * (values.ndim - 1))
         denom = jnp.maximum(jnp.sum(mask) * (values.size // mask.shape[0]), 1.0)
         return jnp.sum(values * w) / denom
     ```
   - For finite-difference velocity ($T-1$) and acceleration ($T-2$) regularizers, construct edge masks `vel_mask = mask[:-1] * mask[1:]` and `acc_mask = mask[:-2] * mask[1:-1] * mask[2:]`.
3. **Slice outputs back to `[:T]`** at the host boundary after optimization or inference completes.

---

## 3. Eliminating Function-Local `@jit` Rebuilds & Closure-ID Cache Misses

Two closely related closure anti-patterns silently defeat JAX/Equinox compilation caching:

### 3a. Function-Local `@eqx.filter_jit` / `@jax.jit` Rebuilt on Every Call (Amortized Over an Inner Batch Loop)
Defining `@eqx.filter_jit def fwd(...)` or `solve = jax.jit(jax.vmap(lambda ...))` *inside* an entry-point function or method (`def decode(...)`, `def place_in_camera(...)`) to capture local variables (`qp`, `k_jax`) in a closure builds a **brand-new function object on every call to the outer function**:

```python
# BAD: `@eqx.filter_jit` is defined inside `decode()` to close over `qp` and `k_jax`.
# Every call to `decode()` creates a fresh `fwd` function object and triggers a full ~9 s
# XLA compile on batch 0. Averaged over T=120 frames (15 batches of 8), the 9 s compile is
# amortized across the loop (`9000 ms / 120 + 4.5 ms ≈ 80 ms/frame`), masquerading as a
# plausible per-frame forward time (~18x slower than true steady state) and throwing away
# the compiled executable as soon as `decode()` returns!
def decode(head, images, K, boxes, valid, *, batch_size=8):
    qp, k_jax = head.query_points, jnp.asarray(K, jnp.float32)

    @eqx.filter_jit
    def fwd(model, ims, bxs, ok):
        return jax.vmap(lambda im, b, v: forward_one(model, qp, im, b[None], v[None], k_jax))(ims, bxs, ok)

    return [fwd(head.device_model, ...) for ...]


# GOOD: Hoisted to module scope with `qp` and `k_jax` passed as explicit traced arguments.
# Compiles once across the entire process lifetime (~4.5 ms/frame warm).
@eqx.filter_jit
def _decode_batch_jit(model, qp, k_jax, ims, bxs, ok):
    return jax.vmap(lambda im, b, v: forward_one(model, qp, im, b[None], v[None], k_jax))(ims, bxs, ok)
```

> **Why `eqx.debug.assert_max_traces` on a function-local definition fails silently:** If you wrap `fwd` with `eqx.debug.assert_max_traces(max_traces=1)` *inside* `decode()`, a fresh guard object is created on every `decode()` call with its trace counter reset to `0`. Within one `decode()` call, all 15 batches have shape `(8, H, W, 3)` so the counter reaches `1` and passes — even when 100 calls to `decode()` compile 100 separate XLA executables! Always hoist both `@eqx.filter_jit` and `assert_max_traces` to **module scope**.

### 3b. Passing Fresh Nested Closures to `vmap` / `jit` / Chunked Primitives
Creating a fresh nested Python closure on every call and passing it to a jitted or cached higher-order primitive misses any cache keyed on `id(fn)` or function identity:

```python
# BAD: Creates a fresh function object `fk` with a new `id(fk)` on every call!
# Any cache keyed on `id(fn)` misses 100% of the time and leaks compiled executables.
def _landmarks_per_frame(state, fk_landmarks, frame_chunk):
    shp, scl, go, gt, bp = state.unpack()
    def fk(g, t, b):
        return fk_landmarks(g, t, b, shp, scl)
    return minibatch_vmap(fk, go, gt, bp, batch_size=frame_chunk)
```

**Fixes:**
1. **Always define `@eqx.filter_jit` / `@jax.jit` functions at module scope** (or bind once in `__init__`), passing call-local arrays (`qp`, `k_jax`, `shp`, `scl`) as explicit traced arguments.
2. **Use callable `eqx.Module` PyTrees or `eqx.Partial` (or unroll closure cells into a PyTree before `@eqx.filter_jit`)** so that captured arrays (`shp`, `scl`, model weights, index tables) are exposed as dynamic traced PyTree leaves while the underlying function code object is static and hashable.
3. **Never key a compilation cache on `id(fn)` without weakrefs or closure unwrapping.** In Python, ephemeral closures either leak forever if stored in the cache or have their `id()` reused after garbage collection for a completely different closure.

---

## 4. Eliminating Host Syncs (`float(loss)`) Inside Training Loops via `jax.lax.scan`

Calling `float(loss_val)` or `np.asarray(grad)` inside a Python `for step in range(num_steps):` loop forces a device-to-host synchronization every step, destroying JAX's asynchronous dispatch (~100–500 $\mu$s dispatch overhead per step) and preventing cross-step XLA fusion.

```python
# BAD: Python loop + per-step device-to-host sync `float(loss_val)`
for _ in range(config.num_steps):
    model, opt_state, loss_val, metrics = train_step(model, opt_state, data)
    loss_history.append(float(loss_val))
```

**Fix — Fuse steps with `jax.lax.scan` inside `@eqx.filter_jit`:**
```python
@eqx.filter_jit
def _run_training_scan(
    model: Model,
    opt_state: optax.OptState,
    data: FitData,
    optimizer: optax.GradientTransformation,
    num_steps: int,
) -> tuple[Model, optax.OptState, Float[Array, "num_steps"], dict[str, Float[Array, ""]]]:
    params, static = eqx.partition(model, eqx.is_inexact_array)

    def _step(carry, _):
        curr_params, curr_opt = carry
        curr_model = eqx.combine(curr_params, static)
        (loss_val, metrics), grads = eqx.filter_value_and_grad(loss_fn, has_aux=True)(
            curr_model, data
        )
        updates, next_opt = optimizer.update(grads, curr_opt, curr_params)
        next_params = eqx.apply_updates(curr_params, updates)
        return (next_params, next_opt), (loss_val, metrics)

    (final_params, final_opt), (losses, metrics_hist) = jax.lax.scan(
        _step, (params, opt_state), None, length=num_steps
    )
    final_model = eqx.combine(final_params, static)
    last_metrics = jax.tree_util.tree_map(lambda x: x[-1], metrics_hist)
    return final_model, final_opt, losses, last_metrics
```
Then transfer `losses` to host **once** after the scan finishes: `loss_history = np.asarray(losses, dtype=np.float64).tolist()`.

---

## 5. Single-Pass Nested `jax.jvp` & Precomputed Static Linear Operators

1. **Simultaneous $(x(t), \dot{x}(t), \ddot{x}(t))$ evaluation for scalar $t$:**
   Using nested `jax.jacfwd` with a separate primal call evaluates the network 3 times per timestamp. Replace with a single nested `jax.jvp` along unit scalar tangent `one = jnp.ones_like(t)`:
   ```python
   def evaluate_single_pos_vel_acc(fn, t: Float[Array, ""]) -> tuple[Array, Array, Array]:
       one = jnp.ones_like(t)
       def val_and_vel(s: Float[Array, ""]) -> tuple[Array, Array]:
           return jax.jvp(fn, (s,), (one,))
       (val, vel), (_, acc) = jax.jvp(val_and_vel, (t,), (one,))
       return val, vel, acc
   ```
   This computes position, velocity, and acceleration in **one single forward-over-forward pass**.
2. **Precompute static Vandermonde / Savitzky-Golay pseudoinverses on CPU with `@functools.lru_cache`:**
   Never call `jnp.linalg.pinv` (SVD) on a static-shape Vandermonde matrix inside a traced function. Compute the filter weights once in NumPy (`@lru_cache`) and convert to a small `jnp.asarray(..., dtype=signal.dtype)` kernel for `jnp.convolve`.

---

## 6. Verifying `xla_compile_count == 1` & `compiles_during_timed == 0`

Every hot jitted function or training loop must be verified against unexpected retracing and function-local `@jit` rebuilds:

1. **In unit tests (`eqx.debug.assert_max_traces` at module scope):**
   ```python
   inner = eqx.debug.assert_max_traces(step_fn, max_traces=1)
   jitted_step = eqx.filter_jit(inner)
   ```
   *(Never place `assert_max_traces` on a function defined inside another function or method — its trace counter resets to `0` on every outer call!)*
2. **Process-wide XLA compile counter (`_CompileCounter`) for benchmarks and end-to-end pipelines:**
   ```python
   import logging
   import jax


   class _CompileCounter(logging.Handler):
       """Counts XLA compilations across the entire process (catches even function-local @jit rebuilds)."""

       n = 0

       def emit(self, record):
           msg = record.getMessage()
           if "Finished XLA compilation" in msg or "Compiling " in msg:
               _CompileCounter.n += 1


   def enable_compile_count():
       jax.config.update("jax_log_compiles", True)
       h = _CompileCounter()
       for name in ("jax", "jax._src.dispatch", "jax._src.interpreters.pxla", "jax._src.compiler"):
           lg = logging.getLogger(name)
           lg.addHandler(h)
           lg.setLevel(logging.WARNING)
           lg.propagate = False
   ```
3. **Interactive diagnostics (`jax.explain_cache_misses` & `jax.log_compiles`):**
   ```python
   with jax.explain_cache_misses():
       out1 = jitted_fn(x1)
       out2 = jitted_fn(x2)  # prints exact leaf/shape/id responsible if a cache miss occurs
   ```

---

## 7. Cold Compile vs. Warm `block_until_ready()` Profiling Protocol

Because JAX dispatch is asynchronous, wall-clock timings without `jax.block_until_ready()` only measure Python enqueue time, and warmup calls without a compile counter can silently hide function-local `@jit` rebuilds. Always benchmark **on the same GPU and inside the same process**:

```python
import time
import jax

enable_compile_count()

# 1. Cold call (compilation + first execution)
t0 = time.perf_counter()
out_cold = jax.block_until_ready(jitted_fn(*args_1))
cold_ms = (time.perf_counter() - t0) * 1e3

# 2. Warm calls (steady-state execution; assert zero XLA compilations during timed window!)
c0 = _CompileCounter.n
warm_times_ms = []
for args_i in warm_inputs:
    t0 = time.perf_counter()
    _ = jax.block_until_ready(jitted_fn(*args_i))
    warm_times_ms.append((time.perf_counter() - t0) * 1e3)
compiles_during_timed = _CompileCounter.n - c0
assert compiles_during_timed == 0, f"Expected 0 warm compiles, got {compiles_during_timed}!"
```

Report:
- **Cold compile + execute latency (ms)**
- **Warm execution latency (ms, median / IQR)**
- **`compiles_during_timed` (`0` required for warm timings) & total compilation count** across $N$ trials / calls (`1` vs. $N$)
- **Numerical parity** (`np.testing.assert_allclose` / relative error) against the reference implementation.
