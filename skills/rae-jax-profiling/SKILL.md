---
name: rae-jax-profiling
description: Canonical RAE standard for JAX/Equinox JIT compilation hygiene, zero-recompilation verification, bf16 tensor-core GEMMs, analytic custom_jvp kinematic Jacobians, multi-iteration lax.scan fusion, and cold-vs-warm profiling across eqx_pose repositories. Use when implementing new JAX/Equinox algorithms, optimizing heavy biomechanics/kinematics/vision/RL loops, fixing JIT/pmap retracing or sharding-flip cache misses, bucket-padding variable-length sequences T, replacing Python training loops with lax.scan, or benchmarking cold compile vs. warm block_until_ready step latency.
---

# RAE JAX Recompilation, Acceleration & Profiling Skill (`rae-jax-profiling`)

This skill consolidates the canonical Reproducible Agent Environment (RAE) standards from `jax-jit-and-fusion`, `jax-memory-and-retracing`, `jax-multi-gpu`, and `jax-config` — together with the general JAX acceleration principles established from `StanfordASL/frax` (`Morton & Pavone 2026`), `XMimic` (`Bohlinger & Peters 2026`), `BodyModels`, and `BiomechanicalFollower` (`KinTwin` / `SuperMimic`) — into a single operational checklist and verification protocol for `/workspaces/eqx_pose`.

Any newly implemented or compute-heavy JAX/Equinox algorithm **must** satisfy the rules below and pass both a **single-compile assertion test** (`max_traces=1` + `jax.monitoring` backend compile listener) and a **cold-vs-warm `jax.block_until_ready()` benchmark**.

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

---

## 8. Indicating Precision in JAX: `jax.default_matmul_precision`, `DotAlgorithmPreset`, and PyTree Policies (Replacing Legacy `jmp`)

JAX controls precision at **two distinct levels**, and neither requires DeepMind's archived `jmp` (`0.0.4`, last released 2022 for Haiku + `float16` loss scaling):

### 8a. Level 1 — Matmul Accumulator & Tensor-Core Precision (`jax.default_matmul_precision` & `DotAlgorithmPreset`)
Even when arrays have dtype `jnp.float32`, NVIDIA GPUs can execute `matmul` / `einsum` / `dot_general` using different hardware instructions. Native JAX (0.10+) provides two built-in ways to specify this without changing array storage dtypes:
1. **Scoped context manager or per-op `precision=` (`jax.default_matmul_precision`):**
   - `with jax.default_matmul_precision("highest"):` (or `precision=jax.lax.Precision.HIGHEST` on a single `jnp.matmul` / `jnp.einsum`): forces full 24-bit IEEE `float32` FMA instead of 10-bit `TF32`. Use this for kinematic trees (`ForwardKinematics`), skinning (`body_models/mhr/skin.py`), and whitening/Cholesky paths.
   - `with jax.default_matmul_precision("bfloat16"):` (or `"tensorfloat32"`): allows `float32` matmuls to round inputs to `bf16` (or `TF32`) on tensor cores while inputs/outputs stay `float32`.
2. **Explicit `jax.lax.DotAlgorithmPreset` (`jax >= 0.4.30` / `0.10.2`):**
   - You can pass an explicit `<LHS>_<RHS>_<ACCUM>` preset directly to `precision=` (e.g., `precision="BF16_BF16_F32"`, `"BF16_BF16_BF16"`, `"TF32_TF32_F32"`, `"F32_F32_F32"`, `"F64_F64_F64"`).

### 8b. Level 2 — Array Storage & Activation Dtype Policy (`param_dtype`, `compute_dtype`, `output_dtype`)
To also halve activation bandwidth and guarantee that **backward** cotangent GEMMs ($\nabla_X = \Delta W^\top$ and $\nabla_W = X^\top \Delta$, which represent $2\times$ the FLOPs of forward) run with `bf16` inputs and outputs on tensor cores, hidden activations themselves must be stored as `jnp.bfloat16`:
- **Why `preferred_element_type=jnp.float32` is a trap on `bf16` matmuls:** NVIDIA tensor cores *already* accumulate `bf16 × bf16` products in `fp32` registers internally even when `preferred_element_type=jnp.bfloat16`. Setting `preferred_element_type=jnp.float32` forces the **layer output** to `float32`, which makes the backward pass's incoming cotangent `float32` and drops both backward GEMMs off the `bf16` tensor cores (`~2x` slower).
- **Why per-layer `jmp.Policy` (`body_models/implicit_representation.py`) is suboptimal inside `vmap`:** Calling `self.jmp_policy.cast_to_compute((self.weight, self.bias, x))` inside `Linear.__call__` when `jax.vmap(implicit_traj)(timestamps)` is mapped over $T$ frames casts the weights inside the per-timestamp `vmap` body (and required forking `eqx.nn.Linear`).
- **Preferred Equinox Pattern — PyTree `cast_to_compute` once outside `vmap` (or a 12-line native `PrecisionPolicy` dataclass):**
  ```python
  @dataclass(frozen=True)
  class PrecisionPolicy:
      param_dtype: jnp.dtype = jnp.float32
      compute_dtype: jnp.dtype = jnp.bfloat16
      output_dtype: jnp.dtype = jnp.float32

      def cast_to_compute(self, tree):
          return jax.tree.map(
              lambda x: x.astype(self.compute_dtype) if eqx.is_inexact_array(x) else x, tree
          )

      def cast_to_output(self, tree):
          return jax.tree.map(
              lambda x: x.astype(self.output_dtype) if eqx.is_inexact_array(x) else x, tree
          )
  ```
  Cast the `eqx.Module` PyTree **once** at the forward boundary (`model_bf16 = policy.cast_to_compute(model_f32)`), run standard `eqx.nn.Linear` / `w @ x` layers (where `bf16 @ bf16` automatically uses `preferred_element_type=jnp.bfloat16` with `fp32` tensor-core accumulation), and cast the final output back via `policy.cast_to_output(y)`. Reverse-mode AD automatically casts the `bf16` weight gradients back to `param_dtype` (`float32`) at the boundary for `optax`.
- **Keep precision-critical operations in `jnp.float32` (or `float64` for Kalman/Gaussian covariances):**
  - Master parameters and Optax/Adam moments (`mu`, `nu`).
  - Running observation normalizers (`RunningMeanStd`) and `LayerNorm` / `RMSNorm` variance reductions.
  - Autoregressive state integration (`next_state = state_f32 + delta_bf16.astype(jnp.float32)`), policy distribution heads (`mean`, `log_std`, `log_prob`), value heads, GAE advantages, and losses.
- **Gate with a single-batch `fp32` vs. `bf16` gradient equivalence test (`test_fast_equiv.py`):**
  - Assert finite losses/gradients and cosine similarity $> 0.999$ between `fp32` and `bf16` parameter gradient vectors on an identical batch.

---

## 9. Analytic `@jax.custom_jvp` Geometric Jacobians Over Kinematic Trees (`frax` Principle)

Calling `jax.jacfwd(residual_fn)(q)` through a general multi-branch biomechanical tree (e.g., 64 bodies, 94 hinge DOFs, 80+ markers/sites) forces forward-mode autodiff to propagate a $94$-column tangent array through every body rotation and translation in the tree — even though each joint column $j$ only moves its descendant bodies. This causes `20–50 s` XLA compile times and `2–10x` slower warm LM/Gauss-Newton steps.

**Rules for Fast Differentiable Kinematics & Inverse Kinematics (`frax` `@morton2026frax` & `BodyModels`):**
1. **Wrap `ForwardKinematics` in `@jax.custom_jvp` using the closed-form geometric Jacobian and a static binary ancestor mask:**
   - Precompute a static binary ancestor mask `M_anc` of shape `(n_bodies, nv)` (or `(n_sites, nv)`) at model load time, where `M_anc[b, j] = 1.0` iff DOF $j$ is on the kinematic path from the root to body/site $b$.
   - In the forward primal pass, compute world body/site positions $\mathbf{p}_b$, world joint anchor positions $\mathbf{p}_j$, and world joint axes $\mathbf{a}_j$.
   - In the JVP rule, compute the exact geometric Jacobian in closed form without tracing through the tree recurrence:
     $$\frac{\partial \mathbf{p}_b}{\partial q_j} = M_{\text{anc}}[b, j] \begin{cases} \mathbf{a}_j \times (\mathbf{p}_b - \mathbf{p}_j) & \text{(revolute / hinge DOF } j\text{)} \\ \mathbf{a}_j & \text{(prismatic / translation DOF } j\text{)} \end{cases}, \qquad \frac{\partial \boldsymbol{\omega}_b}{\partial q_j} = M_{\text{anc}}[b, j]\,\mathbf{a}_j^{\text{rot}}$$
   - Keep `jax.jacfwd` on the outer residual wrapper (`camera_project`, gauge weights, linear/polynomial joint couplings): because `ForwardKinematics` now has a `@jax.custom_jvp` rule, `jacfwd(residual)` automatically invokes the analytic geometric Jacobian for the tree and uses AD only for the thin outer residual assembly.
2. **Force `precision=jax.lax.Precision.HIGHEST` on small $3\times 3$ kinematic matmuls on GPU:**
   - On NVIDIA GPUs, JAX defaults `float32` matmuls to `TF32` (10-bit mantissa), which introduces `~5e-4` to `1.4e-3` drift across chained $3\times 3$ body rotations and lever-arm cross products compared to `mjx.kinematics` / `float64`.
   - Always pass `precision=jax.lax.Precision.HIGHEST` to small $3\times 3$ rotation/tangent matmuls inside FK and its `@jax.custom_jvp` rule; this restores `< 1e-6` GPU `float32` parity at negligible runtime cost.
3. **Serial chains vs. shallow branched trees:**
   - For long **serial** chains (manipulators, continuum spines), use `jax.lax.associative_scan` over $SE(3)$ homogeneous transforms (`frax` parallel scan) to reduce sequential depth from $O(N)$ to $O(\log_2 N)$.
   - For **shallow branched human skeletons** (depth $\le 14$, width $64$), a depth-layered vector gather (`for d in range(1, max_depth + 1):` updating all bodies at depth $d$ in parallel) avoids padding every body to max tree depth.

---

## 10. Catching `pmap`/`pjit` Recompiles via `jax.monitoring` & Fixing Sharding-Flip Bugs

Two multi-device compilation traps frequently waste `25–50 minutes` per training run without appearing in `jax_log_compiles`:

1. **`jax_log_compiles=True` does NOT log `pmap` compilations in modern JAX (`>= 0.4.30` / `0.10+`):**
   - To catch every `jit`, `pjit`, `shard_map`, and `pmap` backend compilation, register a listener on `"/jax/core/compile/backend_compile_duration"` in addition to the log handler:
     ```python
     COMPILE_DURATIONS_S: list[float] = []
     jax.monitoring.register_event_duration_secs_listener(
         lambda event, duration_s: COMPILE_DURATIONS_S.append(duration_s)
         if event == "/jax/core/compile/backend_compile_duration"
         else None
     )
     ```
2. **The `_device_put_sharded` vs. `pmap` `'i'`-Mesh Sharding-Flip Recompile Trap:**
   - Legacy `jax.device_put_replicated(x, devs)` tags array leaves with `NamedSharding(mesh={'_device_put_sharded': N})`, whereas `jax.pmap(..., axis_name='i')` returns leaves tagged with `NamedSharding(mesh={'i': N})`.
   - **Symptom A (Epoch-2 recompile):** Epoch 1 compiles `pmap` for `_device_put_sharded` inputs, and Epoch 2 recompiles the entire `pmap` step (`~40–60 s`) because the carry returned by Epoch 1 now has mesh `'i'`.
   - **Symptom B (Every-eval recompile with `donate_argnums`):** If an evaluator uses `@functools.partial(jax.jit, donate_argnums=(0,))` on `eval_state` while consuming `unreplicate(training_state.params)`, any leaf whose sharding flips between `_device_put_sharded` and `'i'` across calls causes the evaluator to **recompile on every single evaluation** (`~30 s` $\times$ `100` evals = `50 min` wasted).
   - **Fix:** Normalize initial replicated state through a 1-step `pmap(lambda s: s, axis_name="i")` identity (or construct all arrays directly on a single explicit `jax.sharding.Mesh`), strip weak types (`jax.tree.map(lambda x: jnp.asarray(x, dtype=x.dtype) if hasattr(x, "dtype") else x, state)`), and commit unreplicated single-device parameters via `jax.device_put(leaf[0], jax.devices()[0])` before entering any `donate_argnums` evaluator.

---

## 11. Hoisting Loop-Invariant Work Outside `lax.scan` & Deferred 1-GEMM Weight Gradients in Unrolled BPTT

When optimizing recurrent rollouts (`lax.scan` over horizon $H=16\text{--}64$, such as `SuperMimic` world-model imagined rollouts or PPO unrolls):

1. **Hoist all state-independent gathers, encodings, and PRNG splits outside `lax.scan`:**
   - Never slice reference windows via `dynamic_slice_in_dim`, split PRNG keys, or run an MLP encoder on reference/goal inputs *inside* the $H$-step scan body if those inputs do not depend on the evolving recurrent state.
   - Compute the full `(H, B, ...)` reference slice, encoded goal embeddings, and noise tensors **once** in vectorized `(H, B, ...)` form before `lax.scan`, and pass them as the scanned sequence `xs`.
2. **Deferred 1-GEMM-per-layer weight gradients for unrolled BPTT through shared MLPs (`XMimic` `fast_nets.py`):**
   - When backpropagating through an $H$-step `lax.scan` that applies the same MLP weights $W$ at every step, standard reverse-mode AD computes $H$ separate per-step weight gradients $\nabla_{W}^{(t)} = x_t^\top \delta_t$ and accumulates them.
   - For compute-heavy unrolled horizons ($H \ge 16$), a custom VJP that propagates only activation cotangents $\delta_t$ through the sequential recurrence and then computes $\nabla_W = \text{reshape}(X, (H\cdot B, D_{\text{in}}))^\top \text{reshape}(\Delta, (H\cdot B, D_{\text{out}}))$ after the loop replaces $H$ small GEMMs with **one high-occupancy tensor-core GEMM per layer**.
3. **Eliminate redundant value-net forward passes in fixed-length rollouts:**
   - If `episode_length` is fixed inside the scan and `truncation` is identically `False` on steps $0 \dots T-2$, `next_value[t]` equals `value[t+1]`. Evaluate the critic once per step plus one bootstrap call after the loop (`T+1` calls total instead of `2T`), cutting rollout critic compute in half.

---

## 12. Multi-Iteration `lax.scan` Program Granularity, Persistent Cache Hygiene & Sim-vs-Learner Crossover

1. **Multi-iteration `lax.scan` program granularity (`K = 50–100` updates per JIT call) with on-device ring buffers:**
   - Calling separate `collect_step`, `replay_add`, `wm_step`, and `policy_step` JIT functions from a Python `for` loop drains the GPU at every boundary.
   - Fuse trajectory collection, on-device ring-buffer insertion (`jax.lax.dynamic_update_slice_in_dim` along the time/slot axis), uniform window sampling, and learner updates into a single pure carry function scanned over $K \in [20, 100]$ iterations inside one `@eqx.filter_jit(donate="all")` program. Return stacked scalar metrics of shape `(K,)` and log them on the host only once per $K$-iteration chunk.
2. **Persistent XLA compilation cache hygiene (`JAX_INCLUDE_FULL_TRACEBACKS_IN_LOCATIONS=false`):**
   - Configure the persistent XLA cache **before** importing `jax` in training and benchmark entrypoints:
     ```python
     import os
     os.environ.setdefault("JAX_COMPILATION_CACHE_DIR", "/workspaces/eqx_pose/.jax_cache")
     os.environ.setdefault("JAX_PERSISTENT_CACHE_MIN_COMPILE_TIME_SECS", "0")
     os.environ.setdefault("JAX_PERSISTENT_CACHE_MIN_ENTRY_SIZE_BYTES", "-1")
     # Omitting full Python tracebacks from HLO op metadata roughly halves cache load/save time:
     os.environ.setdefault("JAX_INCLUDE_FULL_TRACEBACKS_IN_LOCATIONS", "false")
     ```
3. **Profile the Sim-vs-Learner scaling crossover before optimizing:**
   - Batched GPU physics (`MJX` / `MuJoCo-Warp`) scales **sub-linearly** with `num_envs` until GPU SMs saturate (e.g., `4x` more envs from `512 -> 2048` costs only `1.7x` wall time), whereas large MLP learners (`8×1024` value net over `64` minibatches) are GEMM-bound early and scale **linearly** (`4.7x` wall time for `4x` envs).
   - At `num_envs >= 2048`, the learner often consumes `65–75%` of total iteration wall time while physics is only `25–35%`. Always time `(A) env-step scan only` vs. `(B) full training step` at the production batch/env count so you know whether the bottleneck is physics (`mjx_impl="warp"`, `njmax`, `nconmax`, solver iterations) or the learner (`bf16` GEMMs, critic size, `num_updates_per_batch`).

