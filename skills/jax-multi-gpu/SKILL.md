---
name: jax-multi-gpu
description: >
  Make `jax.pmap` data-parallel training correct, survivable and worth the hardware.
  Use when a multi-GPU run "hangs" with no traceback, when you see "Acquire clique",
  "rendezvous.cc", "Expected N threads to join the rendezvous", "ran out of memory
  trying to allocate" at a checkpoint or validation boundary, "requested by op" with
  a BLANK op name, or a process that is alive but doing no work and holding GPUs.
  Also use proactively BEFORE scaling a single-GPU recipe to several devices: when
  choosing a global batch, adapting a learning-rate schedule, deciding whether more
  GPUs are worth it at all, or writing any code that unreplicates a pmap-replicated
  pytree (checkpointing, validation, visualisation, host-side rendering).
  Complements `jax-memory-and-retracing` (single-device OOMs) and `jax-jit-and-fusion`.
---

# JAX Multi-GPU: Unreplication, Collective Hangs, and Whether Sharding Pays

## Overview

Data-parallel `pmap` training fails in ways single-device training does not, and the
failures are quiet. Three families cover most of it:

1. **Unreplication leaks.** Pulling a replicated pytree back to one device is the most
   common multi-GPU operation and the easiest to get wrong. Done naively it leaves a
   full copy resident on *every* device, permanently.
2. **Collective hangs.** When one replica dies, the others block forever. The process
   stays alive, holds its GPUs, writes nothing, and never returns an exit code.
3. **Scaling that silently changes the experiment.** Every step-counted hyperparameter
   means something different when a step consumes N times the data.

Underneath all three: **your usual instruments lie on multi-GPU.** Process existence,
exit codes, log tails and GPU-utilisation snapshots each report "healthy" for a job
that has been dead for hours.

---

## 1. Unreplication: `x[0]` does not do what it looks like

Under `pmap`, parameters carry a leading device axis. To checkpoint, validate, or render
you need one replica on one device. The obvious code is wrong:

```python
single = jax.tree.map(lambda x: x[0], replicated)   # WRONG
```

`x[0]` selects replica 0, but **the output inherits the input's multi-device sharding**.
The result is not committed anywhere — it stays resident on every device. Under `jit` a
`device_put` *inside* the traced function is a no-op, so the pin must happen outside it.

```python
def unreplicate_to_single_device(tree, device=None):
    """Take replica 0 AND commit it to one device."""
    device = device or jax.devices()[0]
    return jax.tree.map(lambda x: jax.device_put(x[0], device), tree)
```

**Measured cost of getting this wrong** (a ~5 GB model + ~7 GB optimizer state, 2 devices):
`+10.5 GiB on EACH card`, half of it pure waste on the card that never touches the result.

### The leak is the Python local, not the copy

The copy is transient only if you let it be. This pattern pins memory for the rest of the run:

```python
if global_step % save_every == 0:
    model_to_save = unreplicate(model)        # rebound only on the NEXT save
    opt_to_save   = unreplicate(opt_state)    # ...so both stay live in between
    save(model_to_save, opt_to_save)
```

Each local holds its arrays until reassigned. With a save branch, a validation branch and
a visualisation branch, a real trainer accumulated **~25 GB per card of replicated junk**
that was live for the entire run after each branch first executed.

**Rules**
- Route every unreplication through one helper that commits to a device. Never open-code `x[0]`.
- `del` the locals at the end of the branch, or scope them in a function so they fall out.
- Unreplicate the **buffers** too. Constants replicated at setup (SMPL-X bodies, rig tables,
  step constants) carry a device axis as well. A host-side consumer receiving a `(D, G, V, C)`
  array where it expects `(G, V, C)` fails deep inside an einsum, far from the cause.

### Why it surfaces as a giant unrelated allocation

The leaked memory does not fail on its own — it shrinks the margin until *something else*
fails. In one case the failing request was the **pmapped train step's peak workspace**,
~58% of the whole pool, dying with 59% free. Diagnostic tells:

- the request size **varies with model/loss configuration** → it is a computation's workspace,
  not a fixed-size copy of parameters
- the allocator map shows plenty free (`****____...____****`) → not exhaustion, a *margin* problem
- the op name in `requested by op ` is **blank** → no attribution; static reading beats more runs

**Do not chase this by shrinking the memory fraction.** That makes the failure move earlier,
not away — the same request then fails at first-step validation instead of at step 40,000.

---

## 2. Collective hangs: one replica dies, the job does not

When a replica OOMs or aborts mid-collective, the surviving replicas block in the NCCL
rendezvous forever:

```
E rendezvous.cc:116] [rank=1] Acquire clique: devices=2:[0,1]; local_participants=2
  ... has been waiting for 10 seconds and may be stuck.
  Expected 2 threads to join the rendezvous, but not all of them arrived on time.
```

The warning prints once. Then nothing. The process stays alive, holds every GPU, writes no
metrics and never exits.

Note the vocabulary: in a **single-process** `pmap` job (one process, several local devices,
no `jax.distributed`) "rank=0/rank=1" are XLA's per-device **threads**, not processes. There
is no second process to kill.

### The one flag that works

`--xla_gpu_nccl_termination_timeout_seconds=N` aborts the process N seconds after the stall.
Verified by bisection on jaxlib 0.10.1; **these did nothing** and are recorded so nobody retries them:

| tried | result |
|---|---|
| `--xla_gpu_first_collective_call_terminate_timeout_seconds` | parses, hang persisted |
| `--xla_gpu_executable_terminate_timeout` | parses, hang persisted |
| `--xla_gpu_execution_terminate_timeout` | **not a flag** — XLA hard-aborts at startup |
| `NCCL_TIMEOUT`, `NCCL_ASYNC_ERROR_HANDLING`, `NCCL_BLOCKING_WAIT` | **absent from the bundled NCCL** — PyTorch variables, silently no-ops |

XLA flag names are exact-matched with no prefix matching, and an unknown flag is *fatal*.
Verify any flag actually takes effect before relying on it.

Two companions worth setting at the same time:
- **Drop `RLIMIT_CORE` to 0.** The abort writes a core dump — one measured at 17.5 GB into a repo root.
- **Set the flag before `jax` is imported.** `XLA_FLAGS` is read at import.

### Detecting a hang: the only signal that does not lie

| signal | verdict |
|---|---|
| process exists | **useless** — a hung job lives forever |
| exit code | **useless** — never arrives |
| GPU memory allocated | **useless** — a hung job holds it all |
| GPU utilisation snapshot | **useless** — a healthy train loop reads 0% between steps |
| metrics-file mtime | **misleading** — healthy runs batch writes and can look 80+ min stale |
| **CPU-tick delta** | **reliable** — `/proc/<pid>/stat` utime+stime |

A hung process shows ~0–16 ticks per 15 s; a working one shows thousands. Build the watchdog
on that, with a startup grace period long enough for compilation.

---

## 3. Scaling a recipe without changing the experiment

### Every step-counted quantity must be divided

If a step consumes N times the samples, **everything counted in steps reaches its boundary on
N times the data**. Halving two of three is worse than halving none, because the arm looks
subtly wrong rather than obviously wrong.

```
steps_per_epoch          ÷ N
unfreeze/freeze schedules ÷ N
lr_decay_updates / cosine horizon  ÷ N     <-- the one that gets missed
warmup_steps             ÷ N (usually)
eval/checkpoint cadences ÷ N (if you want them at the same data volume)
```

Missing the LR horizon means the schedule completes on N× the data, so at any matched sample
count the arm sits at a **higher** LR — less decayed *and* often a scaled-up peak. It presents
as "multi-GPU is mysteriously less sample-efficient".

**Verify from the run's own saved config, not the launch flags.** Resumes typically rebuild
config from the checkpoint and re-apply only a whitelist of CLI overrides — config *files*
passed on a resume can be silently ignored.

### Divisibility is a hard startup gate

Every batch bucket's `B` must divide the device count — **including eval buckets**, which are
easy to forget and fail only at startup on the larger device count.

### Decide whether sharding pays before you build for it

Two numbers settle it, and neither is throughput:

**Critical batch size.** Above it, more parallelism buys wall-clock and *loses* sample
efficiency. If your critical batch fits on one device, more devices cannot help — and if data
is your binding constraint rather than time, going past it is strictly bad. Fit
`E/E_min = 1 + B/B_crit` to (arm, target) observations across runs; label it as a curve fit,
not a gradient measurement, unless you actually measured gradient statistics.

**Decompose any speedup you quote.** "2 GPUs gave 1.71×" is usually two changes at once — the
extra devices *and* a bigger batch. Measure the batch increase on **one** device first:

```
1.71  =  2 (the doubled batch)  /  1.16 (the sharding tax)
```

That decomposition showed the second device contributed a 16% *overhead* and nothing else,
and that the whole useful batch range fitted on a single card. Comparing an N-GPU arm at
batch 2B against a 1-GPU arm at batch B measures the batch, not the hardware.

### An N-GPU arm is not the same objective as a 1-GPU arm

- **Masked means.** Gradients are `pmean`'d, but a loss term computed as `sum / max(count,1)`
  makes mean-of-per-device-means ≠ global masked mean whenever counts differ across shards.
  Small metric gaps between 1-GPU and N-GPU arms are not signal.
- **Percentiles are wrong.** A `pmean` over per-device percentiles is not a global percentile.
  Means are fine; treat `p50`/`p90`/`p99` as approximate.
- **Contrastive losses change meaning.** Gathering across devices changes the negative-pool
  size, which changes the objective. Check whether a resume path force-enables such a gather —
  resume and fresh launch then optimise different things.

---

## 4. Operational habits that pay for themselves

- **Never mutate a venv while runs are live.** Replacing a package unlinks shared objects the
  running processes have mmap'd; they die silently, staggered, with no diagnostic. Clone the
  venv, mutate the clone, launch new runs against it.
- **Stagger launches.** Two simultaneous XLA compilations of a large program can push load high
  enough that something gets killed with no traceback. Start one, let it compile, then the next.
- **Budget the cold start.** Shuffle-buffer fill plus pmap compilation can take 15–25 minutes
  before the first step. Judging a launch at 20 minutes has twice produced a false "it hangs".
- **Some warnings are permanent noise.** `VMM cuMemCreate with FABRIC+POSIX_FD ...
  CUDA_ERROR_NOT_PERMITTED` appears on every multi-GPU start under container capability limits
  and falls back automatically. Confirm collectives work (`psum` + a large all-reduce) once,
  then stop reading it.
- **Grep for the mechanism, not the string.** Command-buffer formation is a *thunk-level* pass:
  optimized HLO contains `command_buffer` zero times even when buffers are being built. Use
  `TF_CPP_VMODULE=command_buffer_conversion_pass=3`.
- **Checkpoint atomically.** Stage every member to `.tmp` and rename, **metadata last**, so
  "metadata exists" implies a complete set. A non-atomic writer with `keep_last=1` has a window
  (measured at 23–43 s on 12 GB checkpoints) in which a death leaves *zero* resumable checkpoints.

---

## Quick reference

| Symptom | Likely cause | Section |
|---|---|---|
| Alive, 0% util, no metrics, holds GPUs | collective hang after a replica died | §2 |
| `Acquire clique` / `rendezvous.cc` | same | §2 |
| Huge OOM at checkpoint/validation boundary | unreplication residency ate the margin | §1 |
| `requested by op ` with a blank name | not attributable — read the code, don't rerun | §1 |
| Request size varies by model/loss config | it is a computation's workspace, not a copy | §1 |
| Smaller `MEM_FRACTION` makes it fail *sooner* | margin problem, not a leak in that request | §1 |
| N-GPU arm less sample-efficient than 1-GPU | a step-counted schedule was not divided | §3 |
| Startup: batch not divisible by device count | eval bucket, usually | §3 |
| Runs die silently just after a package change | venv mutated under live processes | §4 |
