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
| Every call to a jit'd fn is slow; occasional 10-100x latency outliers | Retracing (static Python scalar or changing shapes) | 1, 2 |
| GPU memory grows step over step inside a "fixed-size" loop | Retained compiled executables from retraces, or an unbounded feature cache | 1, 2 |
| Process disappears mid-run, log ends abruptly, **no Python traceback** | Host OOM-killer (SIGKILL) — usually unbounded host-side accumulation | 4 |
| `XlaRuntimeError: RESOURCE_EXHAUSTED` | GPU OOM — JAX raised it; catchable and diagnosable | 5 |
| OOM during model *loading*, error blames a checkpoint leaf / tree mismatch | Device allocator died mid-deserialize; wrapped as a structure error | 5 |
| Worked yesterday; today jit'd fns fail with version-mismatch / deserialize errors | Stale persistent compilation cache after a cuDNN/driver/jaxlib change | 3 |
| `libcudnn` load errors or cudnn-graph build failures after adding a dependency | Two cuDNN wheels (cu12 vs cu13) colliding, or cuDNN below what jaxlib needs | 6 |
| Memory roughly doubled with no code change | `jax_enable_x64` flipped on (float64 default) | 7 |

## 1. Retracing / Recompilation Leaks

### How the leak happens

`jax.jit` (and `eqx.filter_jit`) cache compiled executables keyed on the
**static** parts of the call: array shapes, dtypes, pytree structure, and
every non-array Python value. Two common ways to leak compiles:

- **Python scalar treated as static.** `eqx.filter_jit` treats anything that
  is not a JAX/NumPy array as static — including plain Python `int`s such as
  a frame index, sequence length, or count. Every new value → a fresh trace,
  a fresh XLA compile, and a *new retained executable*. (`jax.jit` does the
  same for `static_argnums` arguments, and for any int that changes a shape.)
- **Pytree leaf whose shape changes between calls.** E.g. a detector returns
  `(N_kept, H, W)` where `N_kept` depends on a score threshold; every novel
  `N_kept` recompiles all downstream jit'd consumers (resize, IoU, matching).

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

- [ ] All jit'd step functions guarded by an env-gated
      `assert_max_traces(max_traces=1)` + a no-retrace test over the
      shape-varying inputs
- [ ] No Python scalar that varies per call crosses a `filter_jit` boundary
- [ ] Variable-count outputs padded to a static max with a `valid` mask
- [ ] Per-frame outputs streamed or compressed, never appended raw
- [ ] Every cache has an explicit, measured budget
- [ ] `XLA_PYTHON_CLIENT_PREALLOCATE=false` + mem fraction with headroom
- [ ] Persistent compile cache opt-in only; wiped after CUDA/cuDNN changes
- [ ] x64 off globally; bf16 only on validated NN forwards, never on fits

## Related Skills

- `rae:jax-config` — static/dynamic config separation and pytree
  registration; the design-time complement to this skill's diagnosis recipes
  (a correctly-classified config prevents most retrace leaks up front).
- `eqx-porting` (project skill in repos that port PyTorch models to
  JAX/Equinox) — porting workflow, weight conversion, and parity testing;
  use this skill when a ported model's inference loop OOMs or retraces.
