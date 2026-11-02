---
name: jax-memory-and-retracing
description: >
  Diagnose and prevent GPU/host memory OOMs, memory leaks, and JIT retracing in
  JAX/Equinox projects. Use when a process is "killed" with no traceback, when you
  see "OOM", "out of memory", "GPU OOM", "RESOURCE_EXHAUSTED", "memory leak",
  "host RAM grows", "retracing", "recompiling every step", "every step is slow",
  "silent crash / no traceback", "cudnn mismatch", or "cache deserialize error".
  Also use proactively when writing per-frame/per-step loops around jit'd
  functions, accumulating arrays over a long sequence, enabling a persistent
  compilation cache, or choosing float precision for a memory-constrained run.
---

# JAX Memory & Retracing: Diagnose and Avoid OOMs, Leaks, and Recompiles

> Multi-device runs add their own OOM and hang modes — unreplication residency (an
> "unreplicated" tree that is still resident on every device), collective deadlocks, and
> schedule scaling. If the OOM lands at a checkpoint, validation or rendering boundary, or
> the process is alive but doing no work, start at `jax-multi-gpu`.

## Overview

Three failure families account for most "mysterious" crashes in long-running
JAX/Equinox programs:

1. **Retrace leaks** — a jit'd function silently recompiles on every call,
   and every compiled variant is retained, holding device and host memory.
2. **Host-RAM OOM** — Python-side accumulation (frames, masks, caches) grows
   until the Linux OOM-killer SIGKILLs the process with **no traceback**.
3. **GPU OOM** — the device allocator fails, either loudly
   (`RESOURCE_EXHAUSTED`) or disguised as an unrelated error raised mid-operation.

This skill gives symptom → diagnosis → fix recipes for each, plus the
compilation-cache, CUDA/cuDNN packaging, and precision-tiering hazards that
feed them.

## Quick Triage Table

| Symptom | Most likely cause | Section |
|---------|------------------|---------|
| Every call to a jit'd fn is slow; occasional 10-100x latency outliers | Retracing (static Python scalar, changing shapes, or function-local `@jit`) | 1, 2 |
| Batch/sequence helper reports ~50–100 ms/frame "warm" when the inner model is ~5 ms/frame | Function-local `@eqx.filter_jit` / `jax.jit(vmap(lambda ...))` rebuilt on every outer call, amortizing a multi-second compile over the batch loop | 1, 2 |
| GPU memory grows step over step inside a "fixed-size" loop | Retained compiled executables from retraces, or an unbounded feature cache | 1, 2 |
| Process disappears mid-run, log ends abruptly, **no Python traceback** | Host OOM-killer (SIGKILL) — usually unbounded host-side accumulation | 4 |
| `XlaRuntimeError: RESOURCE_EXHAUSTED` | GPU OOM — JAX raised it; catchable and diagnosable | 5 |
| OOM at `jit_step`/first backward; worsens with more views/loss terms; **still OOMs on a 2x-bigger card** | Un-checkpointed backward tape through a large sub-forward (perceptual/teacher/discriminator) in the loss | 5 |
| OOM during model *loading*, error blames a checkpoint leaf / tree mismatch | Device allocator died mid-deserialize; wrapped as a structure error | 5 |
| Worked yesterday; today jit'd fns fail with version-mismatch / deserialize errors | Stale persistent compilation cache after a cuDNN/driver/jaxlib change | 3 |
| `libcudnn` load errors or cudnn-graph build failures after adding a dependency | Two cuDNN wheels (cu12 vs cu13) colliding, or cuDNN below what jaxlib needs | 6 |
| Memory roughly doubled with no code change | `jax_enable_x64` flipped on (float64 default) | 7 |

## 1. Retracing / Recompilation Leaks

### How the leak happens

`jax.jit` (and `eqx.filter_jit`) cache compiled executables keyed on the
**function object identity** plus the **static** parts of the call: array
shapes, dtypes, pytree structure, and every non-array Python value. Three
common ways to leak compiles:

- **Python scalar treated as static.** `eqx.filter_jit` treats anything that
  is not a JAX/NumPy array as static — including plain Python `int`s such as
  a frame index, sequence length, or count. Every new value → a fresh trace,
  a fresh XLA compile, and a *new retained executable*. (`jax.jit` does the
  same for `static_argnums` arguments, and for any int that changes a shape.)
- **Pytree leaf whose shape changes between calls.** E.g. a detector returns
  `(N_kept, H, W)` where `N_kept` depends on a score threshold; every novel
  `N_kept` recompiles all downstream jit'd consumers (resize, IoU, matching).
- **Function-local `@eqx.filter_jit` / `@jax.jit` rebuilt on every outer call
  (and hidden by inner-loop amortization).** A sequence or batch helper
  (`def decode(head, images, K, ...):`) defines `@eqx.filter_jit def fwd(...)`
  or `solve = jax.jit(jax.vmap(lambda ...))` *inside its body* to capture
  call-local variables (`qp`, `k_jax`) in a closure. Within a single `decode()`
  call over $T=120$ frames ($15$ batches of $8$), batch 0 pays a full XLA
  compile (~9 s) and batches 1..14 hit the local cache (~4.5 ms/frame).
  Averaged over $T=120$ frames, `decode()` reports ~80–85 ms/frame — hiding a
  **9-second cold XLA compile** inside what looks like a plausible per-frame
  forward time (~19x slower than true steady state)! Worse, as soon as
  `decode()` returns, the local `fwd` is garbage-collected, so **every
  subsequent call to `decode()` (every video clip, trial, or "warm" benchmark
  repetition) builds a fresh function object and recompiles from scratch**.

Each retained executable holds device memory (baked-in constants, workspace)
and host memory (the lowered program). In a per-frame loop this looks exactly
like a memory leak — GPU usage stair-steps upward until OOM — and each new
variant also costs hundreds of ms to seconds of compile time, visible as
latency spikes.

### Symptoms

- Per-step time never reaches a fast steady state, or shows sporadic
  ~10-100x outliers on specific iterations.
- GPU (and host) memory grows monotonically in a loop that should have a
  fixed working set.
- `JAX_LOG_COMPILES=1` prints a compilation line on calls after the first.

### Fixes

- **Make varying values traced, not static.** Pass `jnp.asarray(x)` instead
  of a bare Python scalar. If the value feeds Python control flow, restructure
  with `jnp.where` / `lax.cond` masks so the trace is value-independent.
- **Keep leaf shapes static: pad to a fixed maximum + validity mask.**
  Instead of returning `(N_kept, ...)`, return top-K with fixed `K = N_MAX`
  and a `(N_MAX,)` bool `valid` mask; downstream ops gate results on `valid`
  so padded slots are inert. Select top-K in pure JAX
  (`jnp.argsort(-scores)[:N_MAX]`), not `np.nonzero` on host.
- **Never branch shapes on Python ints.** Anything like
  `x[:n]` or `jnp.zeros((n, d))` with `n` varying per call must either be
  bucketed (round `n` up to a small set of fixed sizes, e.g. `(8, 16, 32)`)
  or padded to a max. Bucketing bounds compiles to the bucket count.
- **State objects carried across steps must have static shape.** A
  tracker/accumulator pytree passed in and out of a jit'd step must keep
  identical leaf shapes every step — preallocate fixed-capacity slots and a
  ring-buffer index rather than appending.
- **Define `@eqx.filter_jit` / `@jax.jit` functions once at module scope (or
  once in `__init__`), never inside a per-call function or method body.**
  Pass call-local arrays (`query_points`, camera intrinsics `K`, extrinsics) as
  explicit traced arguments instead of capturing them in a function-local
  closure.
- If you *intentionally* discard a set of compiled variants (e.g. after a
  resolution change), call `jax.clear_caches()` to release them.

```python
# WRONG — num_frames is a Python int: filter_jit treats it as static,
# so every distinct value compiles (and retains) a new executable.
@eqx.filter_jit
def step(model, frame, num_frames):
    ...

# RIGHT — traced 0-d array; one compile covers all values.
step(model, frame, jnp.asarray(num_frames))
```

```python
# WRONG — output shape depends on data: every novel count retraces consumers.
keep = np.nonzero(scores >= threshold)[0]
return masks[keep]

# RIGHT — fixed (N_MAX, H, W) + valid mask; shape never changes.
order = jnp.argsort(-scores)[:N_MAX]
return masks[order], scores[order] >= threshold
```

```python
# WRONG — @eqx.filter_jit defined inside decode() to close over qp and k_jax:
# every call to decode() creates a brand-new `fwd` function object and pays a
# full ~9 s XLA compile on batch 0 (amortized across the batch loop to look like
# ~85 ms/frame instead of the true ~4.5 ms/frame steady state!).
def decode(head, images, K, boxes, valid, *, batch_size=8):
    qp, k_jax = head.query_points, jnp.asarray(K, jnp.float32)

    @eqx.filter_jit
    def fwd(model, ims, bxs, ok):
        return jax.vmap(lambda im, b, v: forward_one(model, qp, im, b, v, k_jax))(ims, bxs, ok)

    return [fwd(head.device_model, ...) for ...]


# RIGHT — hoisted to module scope with qp and k_jax passed as traced arguments;
# compiles once across the entire process lifetime.
@eqx.filter_jit
def _decode_batch_jit(model, qp, k_jax, ims, bxs, ok):
    return jax.vmap(lambda im, b, v: forward_one(model, qp, im, b, v, k_jax))(ims, bxs, ok)
```

## 1b. The Inverse: a Cached Trace Silently Absorbing a Change

Section 1 is about retracing too *often*. The same cache key causes the opposite
failure, and it is far harder to see: **jit does not retrace when you needed it
to**, so a change you made has no effect and the code appears to confirm it.

### How it happens

The cache is keyed on the static parts of the call — shapes, dtypes, pytree
structure, non-array Python values. It is **not** keyed on module-level
constants, config values, or any other global the traced code *read*. Change one
of those and call the function again with the same argument structure, and you
get the previous executable back.

```python
# WRONG -- the mutation is absorbed by the cache; the assertion tests nothing.
config.EPS = 1e-5                     # was 1e-6
out = model(x)                        # same shapes -> cached trace, old EPS
assert allclose(out, golden)          # PASSES. Nothing was mutated in the executable.
```

### Where it bites hardest: mutation tests

A mutation test exists to prove a guard has teeth: break the thing it guards,
watch it fail. If the mutation is absorbed by a trace, the test passes and is
recorded as *proven* when it is inert — the worst outcome, because a test nobody
distrusts is worse than no test.

### Fix

Force a re-trace, then confirm the mutation is observable before trusting any
arm that passes:

```python
# Reach the undecorated body, so no cache is consulted at all.
type(model).__call__.__wrapped__(model, x)

# Or clear the caches between arms.
jax.clear_caches()

# Or build a fresh module/closure per arm, so the cache key differs.
```

```python
# And prove the harness can see a mutation at all -- run one arm you KNOW must
# fail, and watch it fail, before crediting an arm that passes.
```

### The same cache defeats memory measurement

A module baked into a closure is a compile-time constant; the same module passed
as a traced argument is not. The two produce different executables and different
peak-memory figures for the same computation. **Measure in the calling convention
you ship**, or the number describes a program you do not run.

Relatedly, `jax.device_get`-style peak counters (`peak_bytes_in_use`, and torch's
`max_memory_allocated`) are **process-lifetime high-water marks**. Several arms in
one process all report the maximum over every arm run so far, which silently
yields an identical figure for arms that differ. One arm, one process.

## 2. Detecting Retraces (Equinox/JAX tooling)

### `JAX_LOG_COMPILES=1` — locate and count compilations

```bash
JAX_LOG_COMPILES=1 python my_script.py 2>&1 | grep -c "Compiling"
```

Every line after warmup is a retrace. The logged function name tells you
*which* jit boundary is unstable; correlate the timestamps with your loop
index to find *what* changed.

### `eqx.debug.assert_max_traces` — hard-fail on unexpected retraces

Wrap the **inner** function, then jit. Order matters: `assert_max_traces`
counts traces of the function it directly wraps, so jit-then-assert would
count outer dispatches (every call), not real compilations.

```python
inner = eqx.debug.assert_max_traces(step_fn, max_traces=1)
jit_step = eqx.filter_jit(inner)
...
eqx.debug.get_num_traces(inner)  # introspect the count at any time
```

Gate it behind an env var so production pays zero overhead and CI can opt in:

```python
def _maybe_guard(fn, registry, name):
    if not os.environ.get("MYPKG_ASSERT_NO_RETRACE"):
        return fn
    inner = eqx.debug.assert_max_traces(fn, max_traces=1)
    registry[name] = inner  # so tests can query get_num_traces(inner)
    return inner

self._jit_step = eqx.filter_jit(_maybe_guard(step_fn, self._guards, "step"))
```

### A no-retrace regression test

The highest-value test in any per-frame/per-step pipeline: exercise the path
that historically changed shapes or scalars, and assert the trace count
stayed at 1. Run it on CPU with a synthetic model — it needs no weights.

```python
def test_step_compiles_once_across_lengths(monkeypatch):
    monkeypatch.setenv("MYPKG_ASSERT_NO_RETRACE", "1")
    runner = make_runner()  # small synthetic config, CPU is fine
    for num_frames in (3, 5, 9):          # values that used to retrace
        runner.run(synthetic_frames(num_frames))
    assert all(n == 1 for n in runner.trace_counts().values())
```

`assert_max_traces` makes the failure loud at the *moment* of the second
trace (with both call signatures in the error), which is far easier to debug
than a downstream OOM hours later.

**Gotcha — `assert_max_traces` on a function-local definition is a guard that
cannot fail across outer calls.** If a helper builds `@eqx.filter_jit` inside
its own function body (`def decode(...): @eqx.filter_jit def fwd(...)`),
wrapping `fwd` with `assert_max_traces(max_traces=1)` *inside* `decode()`
creates a **brand-new guard instance on every `decode()` call** with its trace
counter reset to `0`. Within one `decode()` call, all batches have identical
shape so the counter reaches `1` and passes — completely blind to the fact that
100 calls to `decode()` compiled 100 separate XLA executables! Always hoist
both the `@eqx.filter_jit` function and its `assert_max_traces` wrapper to
module scope, and pair them with a process-wide XLA compile counter in
benchmarks and integration tests:

```python
import logging
import jax


class _CompileCounter(logging.Handler):
    """Process-wide XLA compile counter (catches even function-local @jit rebuilds)."""

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
Assert `_CompileCounter.n - c0 == 0` across all post-warmup calls or timed
benchmark repetitions.

## 3. Persistent Compilation Cache Pitfalls

`jax.config.update("jax_compilation_cache_dir", ...)` persists compiled
executables across processes — a big win when cold compiles take minutes.
Two hazards:

- **Stale-cache poisoning.** The cache key does not capture every runtime
  dimension — notably the cuDNN/driver runtime can change without changing
  the key. After upgrading cuDNN (or jaxlib pulling a different one), the
  cache can serve an incompatible executable, failing with deserialize /
  version-mismatch errors that look like corruption. **Fix:** delete the
  cache directory after any CUDA/cuDNN/jaxlib/driver change. Treat "wipe the
  JAX cache dir" as a standard step in upgrade SOPs.
- **Libraries must not enable it on import.** Setting
  `jax_compilation_cache_dir` is a *global* config flip and a filesystem
  side effect (it silently accumulates GBs). A library that does this on
  import hijacks application policy. **Fix:** make it opt-in via an env var
  or explicit setup call owned by the application:

```python
def setup_compilation_cache(cache_dir: str | None = None) -> Path | None:
    """Opt-in persistent compile cache. Off unless the caller asks."""
    cache_dir = cache_dir or os.environ.get("MYPKG_JAX_CACHE_DIR")
    if not cache_dir:
        return None
    path = Path(cache_dir).expanduser()
    path.mkdir(parents=True, exist_ok=True)
    jax.config.update("jax_compilation_cache_dir", str(path))
    jax.config.update("jax_persistent_cache_min_compile_time_secs", 1.0)
    return path
```

A persistent cache only pays off if nothing retraces — pin that first with
the no-retrace tests from section 2, otherwise the cache just grows.

## 4. Host-RAM OOM: the Traceback-less SIGKILL

### Recognize it

The process **disappears** — log ends mid-line, shell reports `Killed` or
exit code 137 (128+SIGKILL), and there is **no Python traceback**. This is
the Linux/cgroup OOM-killer. `PYTHONFAULTHANDLER` cannot help: SIGKILL is
not interceptable, so faulthandler prints nothing. Do not burn time on
batch-size or GPU mem-fraction knobs — this class is host RAM, not GPU.

Confirm:

```bash
dmesg -T | grep -i "killed process"        # if you have access
# Otherwise: watch host RAM during a repro
while sleep 5; do free -g | awk '/Mem:/{print strftime("%T"), $3" GB used"}'; done
# Or track the process itself:
while sleep 5; do ps -o rss= -p <PID> | awk '{print strftime("%T"), $1/1048576" GB RSS"}'; done
```

Monotonic growth toward the machine's limit = accumulation leak. A flat
plateau that is simply too high = oversized working set (datasets, workers).

### The two canonical causes

**(a) Accumulating O(T) full-resolution arrays over a sequence.** The natural
consumer pattern for a streaming model — "append every frame's masks/frames/
features to a list" — buffers the entire video in host RAM. A single
full-HD float32 mask is ~8 MB; per-object, per-frame, this caps runs at
roughly a thousand frames and then SIGKILLs.

Fixes, in order of preference:
1. **Stream, don't accumulate.** Consume each frame's output inside the loop
   (write to disk, update running stats) and let it go. Provide an iterator
   API so O(1)-memory consumption is the easy path.
2. **Store compactly when you must keep everything.** Binary masks:
   threshold → `np.packbits` → `zlib.compress` is lossless, stdlib-only, and
   ~1000x smaller than float32; decode lazily on access. Frames/features:
   uint8, downsampled, or memory-mapped to disk.
3. **Bound every cache with a real budget.** An "it's only a few MB" LRU
   becomes hundreds of GB when shard sizes grow 100x. Size caches as
   `entries x measured_entry_size x num_workers` against actual host RAM,
   and re-check the bound whenever data size changes. Never ship an
   unbounded `dict` cache on a data path.

**(b) Compiled-executable buildup** from retracing (section 1) — XLA
compilation itself can also transiently spike host RAM by many GB on large
models, so an almost-full host dies *during* a compile, which is confusing:
the leak was the dataset cache, but the killer struck inside JIT.

## 5. GPU-OOM Diagnosis Discipline

### Two distinct presentations

- **Catchable:** `jaxlib.xla_extension.XlaRuntimeError: RESOURCE_EXHAUSTED`.
  JAX raised it; you get a traceback and can reason about which allocation
  failed.
- **Disguised:** the allocator fails midway through a larger operation and
  surfaces as an unrelated error. Classic case: model deserialization OOMs
  partway through the leaf list and presents as a tree-structure /
  leaf-mismatch error naming whatever leaf it died on. If a "structure
  mismatch" appears only on busier GPUs or at lower memory fractions,
  suspect OOM, and check the exception's `__cause__` chain for
  `RESOURCE_EXHAUSTED`.

### Tell GPU from host, leak from working set

Sample both memories over time; the divergent one is your problem:

```bash
# GPU, every 5 s:
nvidia-smi --query-gpu=timestamp,memory.used --format=csv -l 5
# Host, every 5 s:
while sleep 5; do free -m | awk '/Mem:/{print strftime("%T"), $3}'; done
```

- GPU grows stepwise per iteration → retained executables (section 1) or a
  per-step device-array cache you forgot to clear.
- GPU flat but high, fails only at one phase → working set too large for
  that phase; reduce batch/resolution or free the previous phase's arrays
  (drop references, then `jax.clear_caches()` if compiled variants pin them).
- Host grows, GPU flat → section 4.

### Reduce-after-fan-out: scan/chunk, never one wide `vmap`

A common phase-OOM is a **fan-out you immediately reduce**: run the same model
on `N` variants (augmentations, hypotheses, MC samples, ensemble members) and
collapse the `N` outputs to a statistic (mean, std, max, top-k). The natural
`jax.vmap(f)(variants)` materializes **all `N` forwards' activations at once**,
so the peak scales with `N` even though the *result* is tiny. On a large model
(a ViT/backbone × a real batch) a modest `N` (e.g. 8) is enough to exhaust the
device — the failing allocation names the fan-out's executable and is
`N`-proportional.

The fix is to stream the fan-out and reduce online, so only `chunk` forwards
co-reside:

```python
# WRONG — all N augmented forwards live at once; peak ∝ N.
outs = jax.vmap(lambda k: model_forward(augment(x, k)))(keys)   # (N, B, ...)
sigma = jnp.std(outs, axis=0)

# RIGHT — lax.map over chunks; peak ∝ chunk, result identical.
def chunk_fwd(ck):                       # ck: (chunk,) keys
    return jax.vmap(lambda k: model_forward(augment(x, k)))(ck)
outs = jax.lax.map(chunk_fwd, keys.reshape(n_chunks, chunk, *keys.shape[1:]))
sigma = jnp.std(outs.reshape(-1, *outs.shape[2:])[:N], axis=0)
```

`chunk` is a pure memory↔throughput knob — it does **not** change the numerical
result (same `N` samples), so set it small enough to fit the phase and leave `N`
at whatever the statistic needs. For a true O(1)-peak reduction (no `(N, …)`
stack at all), carry a running accumulator through `lax.scan` (e.g. Welford for
mean/variance) instead of stacking then reducing.

**Gotcha — a `chunk` default `>= N` silently collapses to the wide `vmap`.** If
the chunking helper defaults `chunk` to the same value as the fan-out count (or
the caller omits it), `n_chunks == 1` and `lax.map` runs a single group over all
`N` — i.e. the exact wide `vmap` you were avoiding, with no error, just the OOM.
Default `chunk` to a small constant (2–4), and treat `chunk >= N` as the
unguarded wide-`vmap` case in the docstring so callers know it OOMs large models.

### Backward-tape OOM: gradient-checkpoint large frozen sub-forwards used in a loss

A loss term that forwards a **large network on the prediction** — a perceptual /
feature loss (VGG / DINO / CLIP), a frozen teacher, a discriminator — is
differentiable wrt that prediction, so reverse-mode AD must **store the
sub-network's entire activation tape** for the backward pass. The weights being
**frozen does not help**: freezing zeroes the *weight* gradient, but the
*input*-gradient path still needs every intermediate activation. Run the
sub-forward `K` times per step (once per view, timestep, MC sample, or loss
target) and the **backward-tape peak scales with `K x depth x tokens`**, dwarfing
the rest of the step.

**The tell that distinguishes this from a working-set OOM:** the failure strikes
at `jit_step` (the first backward), worsens as you add loss terms or views, and
**does not fit even on a much larger card** — a 2x GPU OOMs the same way, because
the cost is the *tape*, not a one-off buffer. (A working-set OOM, by contrast,
shrinks with batch/resolution and *does* fit when you upsize the card.) If a
perceptual/feature loss makes a run need >2x its base memory, suspect this before
reaching for a bigger GPU.

Fixes, in order:
1. **`jax.checkpoint` (remat) the sub-forward.** Wrap the frozen network's forward
   so its activations are **recomputed in the backward** instead of stored —
   trading compute for memory. Peak drops from `K x full-tape` to roughly
   `K x one-layer`. Value-identical; the single highest-leverage fix.
2. **`stop_gradient` the target branch.** In `d(f(pred), f(gt))`, `f(gt)` needs no
   tape — wrap it so only the `pred` branch is differentiated.
3. **Cut `K`.** Score the term on fewer views/samples; a perceptual loss on the
   single matched view is usually as effective as on all of them at a fraction of
   the memory.

```python
# WRONG — frozen backbone forward on every view; full tape per view -> peak ∝ K.
def feat_loss(pred, gt, mask):
    return jnp.mean(1 - cos(backbone(pred * mask), backbone(gt * mask)))
total = sum(feat_loss(pred[v], gt[v], mask[v]) for v in range(K))   # OOMs at jit_step

# RIGHT — remat the differentiated forward, stop-grad the target, score one view.
backbone_remat = jax.checkpoint(backbone)
def feat_loss(pred, gt, mask):
    f_gt = jax.lax.stop_gradient(backbone(gt * mask))               # no tape
    return jnp.mean(1 - cos(backbone_remat(pred * mask), f_gt))     # recomputed in bwd
total = feat_loss(pred[0], gt[0], mask[0])                          # K = 1
```

This is the backward-pass dual of the forward-peak fan-out above: §"Reduce-after-fan-out"
chunks the *forward* activations of `N` parallel variants; remat recomputes the
*backward* activations of a deep sub-forward. A loss with both (a perceptual term
under a vmap over views) needs both fixes.

### Standardized Cross-Project Toolchain & XLA Flags (`body_models.environment_check`)

Rather than scattering ad-hoc `os.environ["XLA_FLAGS"]` blocks across training scripts, projects in the biomechanics ecosystem share a single, pure-metadata environment checker and configurator in `body_models.environment_check`:

- **Before JAX backend initialization (top of entrypoints / `conftest.py`):** Call `configure_environment()` (or `apply_recommended_flags()`) to idempotently set `XLA_PYTHON_CLIENT_PREALLOCATE=false`, append version-specific XLA workaround flags (such as `--xla_gpu_experimental_gemm_fusion_v2=false` on `jaxlib >= 0.12` to prevent the Triton GEMM nested-`vmap` backward miscompile `openxla/xla#51186`), and configure partitioner workarounds (`JAX_USE_SHARDY_PARTITIONER=false` on `jaxlib == 0.11.2`).
- **Passive runtime verification (`check_environment()` / `find_gotchas()`):** Automatically invoked once per process when `ForwardKinematics` is constructed (and callable directly by any library). Reads `importlib.metadata` and `os.environ` without importing `jax` or touching devices, emitting a `ToolchainWarning` if any known JAX / XLA / cuDNN / NCCL gotcha is active and unmitigated.

### Allocator hygiene

```bash
XLA_PYTHON_CLIENT_PREALLOCATE=false     # see true usage; play nice on shared GPUs
XLA_PYTHON_CLIENT_MEM_FRACTION=0.65     # leave headroom for transients & cohabitants
```

Preallocation off makes `nvidia-smi` meaningful for diagnosis. Choose a
mem fraction that leaves room for allocator transients — peak usage during
loading/compile can briefly exceed steady state by 2x.

Two loading/lifecycle patterns that prevent avoidable GPU OOMs:

- **Deserialize weights to CPU first, then upload once.** Loading a
  checkpoint directly onto the device while a randomly-initialized skeleton
  of the same model is still resident doubles peak device memory. Build /
  deserialize under `jax.default_device(jax.devices("cpu")[0])`, drop the
  skeleton, then `device_put` the array leaves.
- **Own your background jobs.** Backgrounded GPU processes that lose their
  launcher frequently orphan and *keep their device memory*. Before
  relaunching, find and kill your own stale PID (never broad `pkill` on a
  shared machine); before blaming contention, check whether the squatter
  is yours.

## 6. CUDA/cuDNN Dependency Hazards

There is one `libcudnn.so` soname per process — two providers cannot
coexist.

- **Torch pulling CUDA-13.** Default GPU torch wheels can be CUDA-13 builds
  that depend on `nvidia-cudnn-cu13`, which file-collides with
  `jax-cuda12`'s `nvidia-cudnn-cu12` and breaks JAX's cudnn-graph paths.
  **Fix:** if torch is only used for weight conversion or host-side I/O,
  resolve it from the **CPU wheel index** (carries no cuDNN) and put the
  conversion deps behind an optional extra. Only co-install GPU torch when
  it genuinely runs on the GPU, and then match CUDA majors.
- **cuDNN floor below what jaxlib needs.** JAX's declared constraint (e.g.
  `cudnn>=9.x`) can be looser than what its bundled XLA actually needs to
  build cudnn graphs (e.g. flash attention). The resolver then picks a
  too-old patch release and JIT fails at runtime. **Fix:** pin/floor
  `nvidia-cudnn-cu12` (via a constraint, not a direct dep) at a version
  verified against your jaxlib, so fresh clones resolve a working runtime.
- After **any** change in this layer, wipe the persistent compilation cache
  (section 3).

## 7. Precision / Memory Tiering

Precision is a memory knob with sharp numerical edges. Default tiering:

- **float32 is the global default.** Never enable `jax_enable_x64` globally:
  it silently doubles every array and the autodiff tape — a fit that used
  to OOM at 2x memory is the classic signature. If some component needs
  float64 (reference-equivalence tests, a numerically delicate solver),
  gate it behind an explicit opt-in flag scoped to that component.
- **bfloat16 for big NN forwards** (backbones, encoders) is usually safe —
  validate once against f32 (cosine similarity / max-abs on outputs) and
  you halve activation memory and often gain throughput.
- **Never run ill-conditioned optimization in bf16** — second-order /
  line-search fits (LBFGS, IK, bundle-adjust) need f32 minimum; bf16's
  8-bit mantissa destroys convergence. Tier *within* the program: bf16
  forwards feeding an f32 optimizer is a sound and common split.

Rule of thumb: dtype choices are per-subsystem policy, set explicitly at
each boundary — never a global config flip made on import.

## Pre-flight Checklist for Long Sequence/Video Loops

- [ ] All jit'd step functions defined at **module scope** (never inside a
      per-call function/method body) and guarded by a module-scope
      `assert_max_traces(max_traces=1)` + a no-retrace test over the
      shape-varying inputs
- [ ] Warm benchmarks and multi-call integration tests assert
      `compiles_during_timed == 0` via a process-wide `jax_log_compiles`
      handler (catching any hidden function-local `@jit` rebuilds)
- [ ] No Python scalar that varies per call crosses a `filter_jit` boundary
- [ ] Variable-count outputs padded to a static max with a `valid` mask
- [ ] Per-frame outputs streamed or compressed, never appended raw
- [ ] Every cache has an explicit, measured budget
- [ ] `XLA_PYTHON_CLIENT_PREALLOCATE=false` + mem fraction with headroom
- [ ] Persistent compile cache opt-in only; wiped after CUDA/cuDNN changes
- [ ] x64 off globally; bf16 only on validated NN forwards, never on fits
- [ ] Large frozen sub-forwards in a loss (perceptual / teacher / discriminator)
      wrapped in `jax.checkpoint`; target branch `stop_gradient`'d; scored on the
      fewest views/samples that suffice

## Related Skills

- `rae:jax-config` — static/dynamic config separation and pytree
  registration; the design-time complement to this skill's diagnosis recipes
  (a correctly-classified config prevents most retrace leaks up front).
- `eqx-porting` (project skill in repos that port PyTorch models to
  JAX/Equinox) — porting workflow, weight conversion, and parity testing;
  use this skill when a ported model's inference loop OOMs or retraces.
