---
name: jax-jit-and-fusion
description: >
  Find and fix JIT/fusion-hygiene misses in JAX/Equinox code: expensive work
  running eager (un-jitted), under-fused (many tiny jits, or per-element Python
  loops calling un-jitted forwards), or missing `eqx.filter_jit` on a hot path.
  Use when "every step is slow", "GPU sits idle", "low GPU utilization", a model
  "runs eager" / "not jitted" / "per-crop" / "per-frame in a Python loop", or when
  you want to "fuse" ops, choose a "jit boundary", set up `filter_jit`,
  `static_argnums` / `static_argnames`, `donate_argnums` / buffer donation, or
  decide `lax.scan` vs an unrolled loop. Also use proactively before shipping a
  hot inference path, or when benchmarking eager-vs-jit (warm + block_until_ready).
  Complements `jax-memory-and-retracing` — fusion buys speed but can raise peak
  memory and trigger retraces; check both.
---

# JAX JIT & Fusion Hygiene: Don't Run Hot Code Eager or Under-Fused

## Overview

XLA only optimizes what you hand it inside a single `jit`. Code outside a jit
runs **eager**: every primitive op dispatches separately from Python, with no
fusion, no kernel-launch coalescing, and full host round-trips. On a deep model
this is dramatically slower than the same computation compiled once — yet it is
easy to miss, because eager code *works*, produces correct numbers, and shows no
error. The only symptom is that the GPU is starved and the wall-clock is high.

Three failure families:

1. **Eager hot path** — an expensive forward (a ViT/backbone, a decode head) is
   called as a plain `model(x)` per item instead of through `eqx.filter_jit`.
   Per-op Python dispatch dominates. *Worked example below: the MammaNet head ran
   eager per-crop in production; wrapping it in `eqx.filter_jit` was **11x**
   faster.*
2. **Under-fused** — the work *is* jitted, but split across many tiny jit calls
   (or a Python `for` loop calling a small jit per element), so XLA never sees
   enough to fuse and you pay a launch/dispatch tax per op or per iteration.
3. **Wrong boundary** — jit is present but placed too deep (inside the loop body
   only) or too wide (across a batch axis that then OOMs). Boundary placement is
   a speed↔memory trade, not a free win.

This skill gives symptom → diagnosis → fix recipes for each, plus the
`filter_jit` partition rules, `static_argnums`/`donate_argnums`, how to measure
honestly, and the parity caveat (jit ≠ eager bit-for-bit).

## Quick Triage Table

| Symptom | Most likely cause | Section |
|---------|------------------|---------|
| Hot forward called as plain `model(x)` per item; GPU ~idle, wall high | Eager hot path — wrap in `eqx.filter_jit` | 1 |
| `for item in items: jit_small(item)` — per-iteration dispatch tax | Under-fused loop — fuse body, scan, or vmap | 2 |
| Dozens of `@jit` helpers each called once per step | Too-fine jit boundaries — hoist into one outer jit | 2 |
| `jit` is inside the loop body only; outer glue is eager jnp ops | Boundary too deep — jit the largest pure block | 3 |
| Fused a batch axis with `vmap`, now OOM | Boundary too wide — chunk it; see memory skill | 3, 6 |
| Numbers shifted slightly after adding jit; a bit-equality test fails | Expected: XLA fusion reorders fp — gate on the real metric | 5 |
| "Is this actually faster?" unclear from one timer | Async dispatch / cold compile not controlled | 4 |
| Every call recompiles; latency spikes | Static arg or shape varies → retrace | `jax-memory-and-retracing` §1 |

## 1. Eager Hot Path — Wrap the Forward in `eqx.filter_jit`

### How it happens

An Equinox `Module` is callable, so `out = model(image, mask)` just *works* and
returns correct values. But with no enclosing jit, **every primitive inside the
forward dispatches separately from Python** — for a deep ViT that is thousands of
host-driven kernel launches per call, no two of which XLA is allowed to fuse. The
result is correct, silent, and slow.

JAX's own guidance: **"give the XLA compiler as much code as possible, so it can
fully optimize it"** ([jit-compilation guide](https://docs.jax.dev/en/latest/jit-compilation.html)).
A bare `model(x)` gives XLA *nothing*.

### Worked example — the MammaNet head (the anti-pattern that motivated this skill)

The production front-end ran the MammaNet landmark head **eager, once per crop**,
in a Python loop over (camera, frame) crops. Microbench, same GPU / same process,
warm, `block_until_ready`:

```
eager  model(image, mask):              137.9 ms/crop
eqx.filter_jit(model)(image, mask):      12.5 ms/crop   ->  11.0x faster
```

The fix was a one-liner — wrap the per-crop forward:

```python
@eqx.filter_jit
def _jit_forward(model, image, mask):
    return model(image, mask)
```

The crop shape is fixed `((3,512,384) image / (1,512,384) mask)`, so it **compiles
once** and every subsequent crop reuses the fused executable. `filter_jit` caches
on the model's static structure, so a stable model object across crops compiles
exactly once. (See `BiomechMammaNetEqx/src/biomech_mamma_net_eqx/model/frontend.py`.)

### Diagnosis

- Grep the hot path for `model(` / `self.<submodule>(` / `.forward(` calls that
  are **not** lexically inside an `@eqx.filter_jit` / `@jax.jit` function.
- Look for any `Module.__call__` invoked inside a Python `for`/`while` over items
  (crops, frames, people, cameras, hypotheses).
- Confirm it's hot: tie it to the wall-share. Wrapping a 0.1%-of-wall helper buys
  nothing; wrapping the per-crop forward of a 53%-of-wall front-end is the win.

### Fix

Wrap the largest pure forward in `eqx.filter_jit` (not the tiny inner layers).
Keep the **model object stable** across calls so the trace is reused — don't
rebuild or re-partition the module each iteration. Inputs that vary in value but
not shape stay traced automatically (§4 partition rules).

## 2. Under-Fused — Fuse Many Small Ops / Per-Element Calls into One Block

### How it happens

Two shapes of the same mistake:

- **Tiny-jit soup.** Each helper is individually `@jit`-decorated and called once
  per step. XLA optimizes each in isolation and you pay a dispatch/launch tax at
  every boundary between them — work that one enclosing jit would fuse.
- **Per-element Python loop around a small jit.** `for x in xs: y = jit_f(x)`
  drives the GPU one tiny launch at a time from Python, leaving it idle between
  launches (the classic "low GPU util, host-bound" profile).

JAX measured the dispatch cost directly: redefining/re-dispatching trivial jitted
functions in a loop ran **~454 ms** vs **~2.7 ms** for the cached/fused form — a
>100x gap that is pure overhead ([jit-compilation guide](https://docs.jax.dev/en/latest/jit-compilation.html)).

### Fix — pick by loop shape

- **Independent elements, same shape → `vmap` inside one jit.** Batch the element
  axis so XLA fuses across it: `eqx.filter_jit(jax.vmap(f))(xs)`. One launch, full
  occupancy. **Caveat (§6): vmapping a heavy forward over a large batch axis
  materializes every element's activations at once and can OOM** — that is exactly
  why cam-vmap was rejected in BiomechMammaNetEqx (ViT-H × 12 cameras OOM'd at
  every batch size). Chunk the batch if it doesn't fit; see `jax-memory-and-retracing`.
- **Sequential dependence (state carried step→step) → `lax.scan`.** A Python loop
  inside jit is *unrolled* into a giant graph (slow to compile, large); `lax.scan`
  compiles to one XLA `While` and **"is useful for reducing compilation times"**
  ([lax.scan docs](https://docs.jax.dev/en/latest/_autosummary/jax.lax.scan.html)).
  Note scan's main win is **compile time / graph size, not always runtime** — on
  some hardware the rolled loop blocks a few XLA optimizations.
- **Many small jitted helpers → one outer jit.** Drop the inner `@jit`s and wrap
  the composite at the top. Define jitted functions **once at module scope, never
  inside a loop or as a fresh lambda/partial per call** — the cache keys on the
  function's hash, so a redefined-equivalent function recompiles ([guide](https://docs.jax.dev/en/latest/jit-compilation.html)).

```python
# WRONG — host-bound: one tiny launch per element, GPU idle between them.
results = [jit_f(model, x) for x in xs]          # xs all same shape

# RIGHT — fuse the element axis into one jit (watch peak memory, §6).
results = eqx.filter_jit(jax.vmap(jit_f, in_axes=(None, 0)))(model, jnp.stack(xs))
```

## 3. Boundary Placement — Largest Pure Block, but Mind Memory

The right boundary is the **largest contiguous pure-functional block**: ideally
one jit wrapping preprocess-compute-postprocess, with only true I/O / host control
(decode, DB, Python branching on data) outside it.

- **Too deep** — jit only the innermost layer while the surrounding glue stays
  eager jnp ops. Each glue op dispatches from Python. Hoist the boundary outward
  until it encloses the whole pure block.
- **Too wide** — jit (or vmap) across an axis whose fused activations don't fit.
  Speed and memory pull opposite ways here. Don't keep widening blindly; chunk the
  axis (`lax.map` over chunks) so peak ∝ chunk, not ∝ batch. Cross-reference
  `jax-memory-and-retracing` §"Reduce-after-fan-out".
- **Value-dependent control flow** can't go inside jit directly — restructure with
  `jnp.where`/`lax.cond`, or keep that branch outside and jit the two pure arms.

## 4. `filter_jit` Partition Semantics, `static_argnums`, `donate`

### What `eqx.filter_jit` does

**"All JAX and NumPy arrays are traced, and all other types are held static"**,
at the **PyTree-leaf level** — so a single argument can mix traced array leaves
and static non-array leaves ([Equinox transformations](https://docs.kidger.site/equinox/api/transformations/)).
This is why you wrap an `eqx.Module` directly: its array params are traced, its
static structure (and any `eqx.field(static=True)` config) is cached as part of
the compile key.

Consequences to internalize:

- A **Python scalar that varies per call is static** → it retraces on every new
  value. To make it traced, pass `jnp.asarray(x)`. (This is the #1 retrace leak —
  see `jax-memory-and-retracing` §1.)
- **`eqx.field(static=True)` is for genuine config only.** Making a JAX array
  static is almost always a bug; it bakes the array's values into the compile key
  and recompiles when they change. Keep weights/data as normal (traced) leaves.
- Keep the **model object identity/structure stable** across calls so the cached
  trace is reused. Re-partitioning or rebuilding the module each step defeats it.

### `static_argnums` / `static_argnames` (plain `jax.jit`)

Mark an argument static to allow value-based control flow inside the function —
but **"JAX will have to re-compile the function for every new value"**, so it
**"only [works] if the function is guaranteed to see a limited set of static
values"** ([guide](https://docs.jax.dev/en/latest/jit-compilation.html)). Use it
for a handful of fixed configs; never for a per-frame index or per-call count.

### `donate_argnums` / buffer donation

If an input is **not needed after the call** and **matches an output's shape and
dtype**, donate its buffer so XLA reuses that memory for the output — **"This will
reduce the memory required for the execution by the size of the donated buffer"**
([buffer donation](https://docs.jax.dev/en/latest/buffer_donation.html)). The
hard rule: **"It is not allowed to donate a buffer that is used subsequently"** —
reuse raises an error. Donation is positional-args only, and follows pytrees.
Best fit: in-place-style state carried through a step (optimizer/tracker state)
where the old buffer is dead after the update. `eqx.filter_jit(donate="all")` /
`"all-except-first"` apply this with leaf-level filtering.

## 5. Parity Caveat — jit ≠ eager Bit-for-Bit

**Adding jit changes the numbers slightly.** XLA fuses and reorders
floating-point ops, so a jitted forward is **not byte-identical** to the eager
one. In the MammaNet head case: landmark coords shifted `max ~4e-4` normalized
(~0.16 px de-normed), probabilities `max ~4.5e-3`.

Therefore:

- **Do not gate a jit change on bit-equality** — it will fail for a correct
  change. A council "it'll be bit-equal" expectation is usually wrong.
- **Gate on the metric that matters end-to-end** — reprojection error, MPJPE, the
  DB-row values a consumer reads — within a tolerance, not `==`.
- Flag any jit change that feeds a downstream **exact-match** assertion or a
  byte-identical DB/cache key; loosen those to metric tolerances.

## 6. How to Measure (so the win is real, not noise)

Eager-vs-jit and fused-vs-unfused A/Bs are only trustworthy if you control the
confounds — same hardware, warm, synchronized:

1. **Same GPU, same process.** Never compare GPU-A eager vs GPU-B jit (arch/clock
   confound). Run both arms back-to-back on one card.
2. **Warm, post-compile.** The first call pays a one-time XLA compile (seconds to
   minutes). Do a warmup call, *then* time. Report warm and cold separately.
3. **`block_until_ready()` — mandatory.** JAX dispatch is async; without it you
   time the dispatch, not the compute ([guide](https://docs.jax.dev/en/latest/jit-compilation.html)).
   ```python
   jax.block_until_ready(jit_f(model, x))          # warmup + compile
   t0 = time.perf_counter()
   for _ in range(reps):
       out = jax.block_until_ready(jit_f(model, x))
   ms = (time.perf_counter() - t0) / reps * 1e3
   ```
4. **Watch GPU util as the inefficiency signal**, not the score. Low util on a
   high-wall phase = host-bound / under-fused (the thing to fix); the score is
   still wall-clock. (`nvidia-smi dmon`, or a profiler trace via
   `jax.profiler.trace` → TensorBoard for a per-op breakdown.)
5. **Confirm it compiles once, not per call** — `JAX_LOG_COMPILES=1` should print
   one compile then go quiet. Repeated compiles mean a retrace, not a fusion win
   (→ `jax-memory-and-retracing`).

## Pre-flight Checklist for a Hot Inference Path

- [ ] The expensive forward is inside `eqx.filter_jit` / `jax.jit`, not eager
- [ ] No `Module.__call__` / heavy op in a bare Python per-item loop
- [ ] One jit wraps the largest pure block; no tiny-jit soup, no per-call lambdas
- [ ] Independent same-shape elements vmapped (chunked if the batch OOMs)
- [ ] Sequential state loops are `lax.scan`, not Python-unrolled
- [ ] No per-call Python scalar crossing the jit boundary (pass `jnp.asarray`)
- [ ] `static=True` only on real config; weights/data stay traced
- [ ] Benchmarked warm, same-GPU, same-process, with `block_until_ready`
- [ ] Gated on reproj/MPJPE/metric within tolerance, NOT bit-equality
- [ ] `JAX_LOG_COMPILES=1` shows a single compile, not per-call retraces

## Related Skills

- `jax-memory-and-retracing` — the complement to this skill. Fusion buys speed but
  **raises peak memory** (a wide `vmap`/jit materializes all activations at once →
  OOM; chunk it) and a mis-set boundary can **retrace** (a static scalar/shape that
  varies). Use that skill when fusing makes a path OOM or recompile, and for the
  no-retrace `assert_max_traces` regression test that locks the win in.
- `jax-config` — static/dynamic config separation and pytree registration; the
  design-time complement that prevents most static-vs-traced boundary mistakes.
