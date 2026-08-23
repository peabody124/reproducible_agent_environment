---
name: jax-multi-gpu
description: >
  Make multi-GPU JAX data-parallel training correct, survivable and worth the hardware —
  both legacy `jax.pmap` and its `jax.jit` + `NamedSharding` / `jax.shard_map` replacement.
  Use when a multi-device run "hangs" with no traceback, when you see "Acquire clique",
  "rendezvous.cc", "Expected N threads to join the rendezvous", "has been waiting for N
  seconds and may be stuck", "Received incompatible devices for jitted computation",
  "ran out of memory trying to allocate" at a checkpoint / validation / rendering boundary,
  "requested by op " with a BLANK op name, an error blaming a jitted function that contains
  no such op, or a process that is alive, holds every GPU and does no work. Also use
  proactively BEFORE scaling a single-GPU recipe: choosing a global batch or LR schedule,
  deciding whether more GPUs pay at all, migrating off `pmap`, or writing any code that
  unreplicates a replicated pytree (checkpointing, validation, visualisation, host-side
  rendering, `device_put`, `x[0]`).
  Complements `jax-memory-and-retracing` (single-device OOMs) and `jax-jit-and-fusion`.
---

# JAX Multi-GPU: Unreplication, Collective Hangs, and Whether Sharding Pays

## Overview

Data-parallel multi-device training fails in ways single-device training does not, and the
failures are quiet. Three families cover most of it:

1. **Unreplication / placement bugs.** Pulling one replica of a replicated pytree back to one
   device is the most common multi-GPU operation and the easiest to get wrong. Done naively it
   leaves a full copy resident on *every* device, permanently — or, under the modern sharding
   API, silently returns the wrong numbers.
2. **Collective hangs.** When one replica dies, the others block forever. The process stays
   alive, holds its GPUs, writes nothing, and never returns an exit code.
3. **Scaling that silently changes the experiment.** Every step-counted hyperparameter means
   something different when a step consumes N times the data.

Underneath all three: **your usual instruments lie on multi-GPU.** Process existence, exit
codes, log tails, GPU-utilisation snapshots and even the op name in the error each report
"healthy" — or point at the wrong place — for a job that has been dead for hours.

**Evidence tags.** Claims below are marked **[M]** measured (reproduced on jax/jaxlib 0.10.1,
CUDA plugin, in an environment you can re-run the snippet in), **[C]** cited (upstream docs or
source, not re-measured here), or **[F]** field report (observed once on one project's hardware
— directionally true, do not treat the number as a constant).

---

## 0. `pmap` is in maintenance mode — know which API you are in

`pmap` is in **maintenance mode** — not formally deprecated (it emits no `DeprecationWarning`
**[M]**), but the JAX 0.8.0 changelog is explicit **[C]**:

> *"`jax.pmap` is in maintenance mode and we encourage all new code to use `jax.shard_map`
> directly."*

and jaxlib 0.10.1's own `jax.pmap` docstring opens with **[M]**:

> *"Old way of doing parallel map. Use `jax.shard_map` instead."*
> *"`pmap` is now implemented in terms of `jit` and `shard_map`."*
> — with a pointer to the [pmap migration guide](https://docs.jax.dev/en/latest/migrate_pmap.html).

Note the recommended successor is **`shard_map`**, not "jit + sharding" generically.
[JEP 14273](https://docs.jax.dev/en/latest/jep/14273-shard-map.html) gives the reason that matters
here **[C]**: *"the sharding of `pmap` outputs can't be expressed as `Sharding`s/`OpSharding`s, due
to `pmap`'s stacking rather than concatenative semantics."* That mismatch is the root of §1.

**[M]** `jax.device_put_replicated` and `jax.device_put_sharded` are **already gone** from
`jax` 0.10.1; code that calls them will `AttributeError`. The replacement is an explicit mesh:

```python
devices = jax.devices(); n = len(devices)
mesh = jax.sharding.Mesh(np.asarray(devices), ("devices",))
row  = jax.sharding.NamedSharding(mesh, jax.sharding.PartitionSpec("devices"))
replicated = jax.tree.map(
    lambda x: jax.device_put(jnp.broadcast_to(x[None], (n, *jnp.shape(x))), row), tree)
```

**[M]** Also present in 0.10.1 and worth knowing before you write a shim: `jax.shard_map`,
`jax.smap`, `jax.make_mesh`, `jax.set_mesh`, `jax.sharding.reshard`,
`jax.sharding.make_single_device_sharding`, `jax.sharding.AxisType` / `auto_axes` /
`explicit_axes`.

Which API you are in changes the *shape of the bug*, not whether you have one — see §1.4.
**Nothing in §1 or §2 is pmap-specific:** pmap now runs on the same `jit`+`shard_map`
machinery, and the residency behaviour reproduces identically through a plain
`NamedSharding` **[M]**.

---

## 1. Unreplication: `x[0]` does not do what it looks like

Under `pmap` (or a pmap-shaped mesh layout) parameters carry a leading device axis. To
checkpoint, validate, or render you need one replica on one device. The obvious code is wrong:

```python
single = jax.tree.map(lambda x: x[0], replicated)   # WRONG
```

`x[0]` selects replica 0's **values**, but **the output inherits the input's multi-device
sharding**: `PartitionSpec("devices")` becomes `PartitionSpec()` on the same mesh — i.e. *fully
replicated*, a complete copy resident on every device in the job. It is not "uncommitted and
therefore free"; the bytes are really there.

Upstream documents exactly this, in the pmap migration guide's appendix **[C]**:

> *"**JAX does not track semantic replication.** It does not 'know' that the shard on device 1 is
> identical to the shard on device 0. Therefore, when you call `x[0]`, JAX must satisfy the strict
> semantics of array indexing… This triggers a **global gather** (or broadcast) of the entire
> array to all devices before slicing."*

and explains why the idiom used to be free: `PmapSharding` *"had a fast-path optimization in
`jax.Array`'s `__getitem__` allowing it to return an array with a `SingleDeviceSharding`"* — a
fast path that was **removed** along with `PmapSharding` in jax 0.10 **[C]**, because it *"breaks
the semantics of array indexing"*. So code that was correct-and-cheap under old pmap became
correct-and-ruinous without a single line changing.

### 1.1 Prove it in twelve lines (no GPU needed)

**[M]** Runs on CPU with fake devices; the semantics are platform-independent.

```python
import math, jax, jax.numpy as jnp, numpy as np
# XLA_FLAGS="--xla_force_host_platform_device_count=4" JAX_PLATFORMS=cpu
D = jax.devices(); mesh = jax.sharding.Mesh(np.asarray(D), ("d",))
row = jax.sharding.NamedSharding(mesh, jax.sharding.PartitionSpec("d"))

def resident(a):  # device bytes actually held, summed over every device it sits on
    return math.prod(a.sharding.shard_shape(a.shape)) * a.itemsize * len(a.sharding.device_set)

x = jax.device_put(jnp.zeros((len(D), 1024, 1024)), row)      # one replica per device
for name, a in (("x[0]", x[0]), ("device_put(x[0], D[0])", jax.device_put(x[0], D[0]))):
    print(f"{name:24s} logical {a.nbytes/2**20:5.1f} MiB  resident {resident(a)/2**20:5.1f} MiB "
          f" devices {len(a.sharding.device_set)}")
```

```
x[0]                     logical   4.0 MiB  resident  16.0 MiB  devices 4
device_put(x[0], D[0])   logical   4.0 MiB  resident   4.0 MiB  devices 1
```

`jax.debug.visualize_array_sharding` says the same thing in one line **[M]**:

```
x                        x[0]                device_put(x[0], D[0])
┌──────────┐             ┌───────────┐       ┌───────┐
│  CPU 0   │             │CPU 0,1,2,3│       │ CPU 0 │
├──────────┤             └───────────┘       └───────┘
│  CPU 1   │  …
```

### 1.2 The fix, and why each guard is load-bearing

```python
def unreplicate_to_single_device(tree, device=None):
    """Take replica 0 AND commit it to one device."""
    target = device if device is not None else jax.devices()[0]

    def take_replica_zero(leaf):
        # Non-array and 0-d leaves carry no device axis. `3.0[0]` is a TypeError and
        # `jnp.float32(3.0)[0]` is an IndexError, so an unguarded tree.map over a real
        # Equinox module or config pytree crashes before it ever leaks anything. [M]
        if not hasattr(leaf, "shape") or getattr(leaf, "ndim", 0) == 0:
            return leaf
        return jax.device_put(leaf[0], target)

    return jax.tree.map(take_replica_zero, tree)
```

- **`jax.device_put(x, device)` is the whole fix.** Its docstring: *"If given, then the result
  is **committed** to the device(s)"* **[C]**. Verified to produce
  `SingleDeviceSharding(device=0)` **[M]**.
- **The pin must happen outside `jit`.** A `device_put` *inside* a traced function does not
  commit: with a `Device` or a `NamedSharding` it is **silently ignored** and the result comes back
  on all devices **[M]** (upstream: [jax#6040](https://github.com/jax-ml/jax/issues/6040), *"sticky
  device (device_put) ignored in jit context"*); with a `SingleDeviceSharding` it **raises**
  `ValueError: … device_put inside jit with device ids [0]` **[C]**. A maintainer's summary
  **[C]**: *"the recommendation is to use `device_put` outside `jit`, and if you want to constrain
  shardings of an intermediate inside jit, then `with_sharding_constraint` is the API."*
  Single-device extraction is strictly a top-level operation — `jit(..., out_shardings=
  SingleDeviceSharding(d0))` under a multi-device mesh raises the incompatible-devices error too
  **[C]**.
- **Per leaf, not per tree.** `jax.device_put(whole_tree, device)` raises
  `TypeError: Argument 'x' of type <class 'str'> is not a valid JAX type` on the first
  non-array leaf **[M]** — so you need the map and the guards anyway, and mapping keeps the
  replicated intermediate one leaf wide instead of one tree wide.
- **`donate=True` does not rescue you.** `jax.device_put(x[0], D[0], donate=True)` left the
  source array **not** deleted (`is_deleted() == False`) **[M, CPU backend]**; donation is
  documented as best-effort. Drop the reference instead.

### 1.3 Two symptoms, one bug

**Loud.** Mixing a properly pinned array with a naively "unreplicated" one inside a `jit`
fails immediately **[M]**:

```
ValueError: Received incompatible devices for jitted computation.
  Got argument a … with device ids [0] on platform CPU and
      argument b … with device ids [0, 1, 2, 3] on platform CPU
```

This is the *good* outcome — it names the bug. In practice it appears wherever a host-side
consumer combines a device-0 batch slice with a replicated model: an eager sanity forward, a
`lax.cond` / `select_n` over a validity mask, an overlay renderer **[F]**.

**Quiet.** If nothing ever mixes device sets, the copies just sit there and shrink the margin
until *something else* fails. **[F]** On a 2-GPU run, params + Adam state unreplicated this way
charged ~**10.5 GiB to each card**, half of it on the card that never reads the result.

#### The leak is the Python local, not the copy

The copy is transient only if you let it be. This pattern pins memory for the rest of the run:

```python
if global_step % save_every == 0:
    model_to_save = unreplicate(model)        # rebound only on the NEXT save
    opt_to_save   = unreplicate(opt_state)    # ...so both stay live in between
    save(model_to_save, opt_to_save)
```

Each local holds its arrays until reassigned. With a save branch, a validation branch and a
visualisation branch, a real trainer accumulated **~25 GB per card** of replicated junk that was
live for the entire run after each branch first executed **[F]**.

**Rules**
- Route every unreplication through one helper that commits to a device. Never open-code `x[0]`.
- `del` the locals at the end of the branch, or scope them in a function so they fall out.
- Unreplicate the **buffers** too. Large constants replicated at setup (mesh templates, lookup
  tables, per-step constants) carry a device axis as well. A host-side consumer receiving a
  `(D, G, V, C)` array where it expects `(G, V, C)` fails deep inside an einsum, far from the cause.

### 1.4 Under the modern API the same mistake is *worse*

**[M]** In a `jax.jit` + `NamedSharding` data-parallel program, parameters are **replicated**
(`PartitionSpec()`), not stacked — there is **no leading device axis to index**. `x[0]` then
returns the first *element of the data*:

```python
p = jax.device_put(jnp.arange(4.), NamedSharding(mesh, P()))
p.shape        # (4,)  — no device axis
p[0]           # 0.0   — a DATA element, not a replica. Silently wrong.
```

The fix needs no indexing at all, and it is the single most useful line in this skill:

```python
single = jax.device_put(params, jax.devices()[0])                      # or
single = jax.device_put(params, jax.sharding.SingleDeviceSharding(jax.devices()[0]))
```

Both produce `SingleDeviceSharding` **[M]**. So: **migrating off `pmap` removes the residency
trap entirely — but only if you also delete the `x[0]`.** Porting the indexing forward converts
a memory bug into a correctness bug. Grep for `[0]` in every unreplication path as part of the
migration.

The mode matters too **[M]**. On an **Auto** mesh (what `Mesh(devices, ("d",))` gives you by
default) `x[0]` silently performs the gather described above. Give the mesh **Explicit** axis
types and the same expression **raises** instead:

```
ShardingTypeError: … out sharding could not be resolved unambiguously
  (or would require collectives on inputs). Use .at[...].get(out_sharding=) …
```

That is a good reason to adopt explicit axis types on new code: the failure becomes loud. In
Explicit mode the resharding API is `jax.sharding.reshard` / `jax.reshard`, and
`with_sharding_constraint` degrades to an *assertion* rather than a constraint **[C]**.

### 1.5 Do not unreplicate at all if your checkpointer is distributed

§1 assumes a **single-writer serialiser** that reads one complete tree from one device. That is a
property of your checkpointing code, not a law. A distributed checkpointer (Orbax) inverts it:
*"each process first writes its own data independently to its corresponding subdirectory"* and
then merges metadata, and `save` is *"called on all available controller processes"* **[C]**.
`device_get` / `process_allgather` / gathering to one device appear nowhere in its idiom.

So decide once, and write it down: **either** you gather to one device and pay §1's attention tax,
**or** you write shards in place and never unreplicate. Doing the first while believing you are
doing the second is how the residency bug survives review.

### 1.6 Assert placement; don't hope for it

Put this in a test, not in a comment. It runs on CPU fake devices in seconds.

```python
def assert_single_device(tree, what):
    for path, leaf in jax.tree_util.tree_leaves_with_path(eqx.filter(tree, eqx.is_array)):
        n = len(leaf.sharding.device_set)
        assert n == 1, f"{what}{jax.tree_util.keystr(path)} lives on {n} devices"
    resident = sum(resident_bytes(l) for _, l in ...)
    assert resident == sum(l.nbytes for _, l in ...)   # no hidden replicas
```

Then take the same measurement **across a whole save cycle**: building the checkpoint copies
must add exactly one tree's worth of device bytes to `jax.live_arrays()`, and dropping them must
return you to the baseline. That catches the lifetime half of the bug, which the per-leaf
assertion cannot see.

**Gotcha [M]:** compute resident bytes from
`arr.sharding.shard_shape(arr.shape) × itemsize × len(arr.sharding.device_set)`, **not** from
`arr.addressable_shards` — reading `addressable_shards` materialises single-device `Array`
objects that then show up in `jax.live_arrays()` and corrupt the very accounting you are doing.

**Use `x.sharding.num_devices == 1`** as the assertion. `is_fully_replicated` is *not* a
single-device test — it is `True` both for a one-device array and for an N-device replicated one
**[M]**, which is precisely the state you are trying to detect. `x.devices()` works but is
undocumented **[C]**. Other useful diagnostics: `x.sharding`, `x.committed`, `x.device` (returns a
`Device` for single-device arrays and a `Sharding` otherwise), `len(x.addressable_shards)`, and
`jax.debug.visualize_array_sharding(x)` **[M]**. And
`jax.transfer_guard("disallow")` names the destination sharding of any transfer it blocks,
which is a cheap way to catch an unintended host round-trip **[M]**:

```
JaxRuntimeError: INVALID_ARGUMENT: Disallowed host-to-device transfer:
  aval=ShapedArray(float32[3]), dst_sharding=SingleDeviceSharding(device=CpuDevice(id=0) …)
```

### 1.7 Why it surfaces as a giant unrelated allocation

The leaked memory does not fail on its own — it shrinks the margin until *something else* fails.
**[F]** In one case the failing request was the pmapped train step's peak workspace, ~58% of the
whole pool, dying with 59% free. Diagnostic tells:

- the request size **varies with model/loss configuration** → it is a computation's workspace,
  not a fixed-size copy of parameters
- the allocator map shows plenty free (`****____...____****`) → not exhaustion, a *margin* problem
- the op name in `requested by op ` is **blank** → no attribution; static reading beats more runs

**Do not chase this by shrinking the memory fraction.** That makes the failure move earlier, not
away — the same request then fails at first-step validation instead of at step 40,000.

**Related trap:** JAX dispatch is async, so a device error is raised at the next synchronisation
point and blamed on **whatever executable is being awaited there**, which is often a small,
innocent function. **[F]** A failing linear-algebra op inside a pmapped train step surfaced as
`JaxRuntimeError … [executable_name='jit_extract_single_device_model']` — a function that is a
pure per-leaf slice and contains no such op. Before believing the named op, dump the HLO of the
*step* (`--xla_dump_to`) and enumerate its custom calls, or force synchronisation
(`block_until_ready`) immediately after each stage to localise it.

---

## 2. Collective hangs: one replica dies, the job does not

When a replica OOMs or aborts mid-collective, the surviving replicas block in the rendezvous
forever:

```
E rendezvous.cc:116] [rank=1] Acquire clique: devices=2:[0,1]; local_participants=2
  ... has been waiting for 10 seconds and may be stuck.
  Expected 2 threads to join the rendezvous, but not all of them arrived on time.
```

The warning prints once. Then nothing. The process stays alive, holds every GPU, writes no
metrics and never exits. **XLA's default is to warn and then wait forever.**

Note the vocabulary: in a **single-process** job (one process, several local devices, no
`jax.distributed`) "rank=0/rank=1" are XLA's per-device **threads**, not processes. There is no
second process to kill.

### 2.1 Arm a timeout — but arm the RIGHT one

One function (`xla/service/rendezvous.cc`) emits that message for **four different rendezvous
points**, each with its own timeout pair. The name in the message is the whole triage **[C]**:

| name in the log | terminate flag | default |
|---|---|---|
| `Acquire clique` / `Initialize clique` | `--xla_gpu_nccl_termination_timeout_seconds` | **−1 = never** |
| `first call … collective operation` | `--xla_gpu_first_collective_call_terminate_timeout_seconds` | 40 s |
| `thunk initialization completion …` | `--xla_gpu_executable_terminate_timeout` | 30 s |
| whole-execution deadlock (not a rendezvous) | `--xla_gpu_execution_terminate_timeout` | **`inf`** |

So an `Acquire clique` hang lasts forever by default while a first-collective-call hang already
self-terminates. **[F]** That is why, on an `Acquire clique` stall, only
`--xla_gpu_nccl_termination_timeout_seconds` ended the process and the other `*_terminate_*` flags
looked inert — they arm rendezvous the job never reached. **Match the flag to the name in the log;
do not bisect the family.**

A set that parses on jaxlib 0.10.1 **[M]** and covers all four:

```bash
export XLA_FLAGS="\
--xla_gpu_nccl_termination_timeout_seconds=600 \
--xla_gpu_execution_terminate_timeout=10m \
--xla_gpu_execution_progress_tracking=16 \
--xla_gpu_executable_warn_stuck_timeout=60 --xla_gpu_executable_terminate_timeout=600 \
--xla_gpu_first_collective_call_warn_stuck_timeout_seconds=60 \
--xla_gpu_first_collective_call_terminate_timeout_seconds=600"
```

Four things to know before you touch these — the details, defaults and verbatim help strings are
in **`references/collective-hang-toolkit.md`**:

- **The terminate timeout dumps every thread's stack** (`DumpAllThreadStacksToLog`) before its
  `LOG(FATAL)` **[C]**. That is the best artefact you will get; an external `kill` gets you none.
- **A malformed flag VALUE and an unknown flag NAME are different fatals**, and both kill the job
  at first device use with a `F…` line that reads like a driver fault **[M]**. The single most
  expensive instance: `--xla_gpu_execution_terminate_timeout` takes a **duration string** (`10m`,
  `600s`) — passing `=60` fails, and reading that failure as "not a flag" discards the one knob
  whose stated purpose is *"to prevent undetected deadlocks"*.
- **`NCCL_TIMEOUT` / `NCCL_ASYNC_ERROR_HANDLING` / `NCCL_BLOCKING_WAIT` are PyTorch variables.**
  Absent from NCCL's documented variable list **[C]** and from the bundled `libnccl.so.2` **[M]**;
  in a JAX job they do nothing. Use `NCCL_DEBUG` / `NCCL_DEBUG_SUBSYS` / `NCCL_DEBUG_FILE`.
- **Not every stuck warning is a hang.** The same code logs *"Warning above was a false-positive.
  Perhaps the timeout is too short"* when threads merely arrived late **[C]** — uneven per-device
  work under `pmap` produces exactly this. Raise the *warn* timeout; do not chase a bug.

**When to set them.** `XLA_FLAGS` is parsed **once, at the first XLA backend initialisation** —
*not* at `import jax` **[M]**: with a bogus flag set, `import jax` succeeds and the abort only
arrives when the first array touches a device. Setting it before importing `jax` is still the right
rule, but audit the guard from the *program's own log of its effective `XLA_FLAGS`*, never from
import order. Also **drop `RLIMIT_CORE` to 0** first — the abort writes a core dump, one measured
at 17.5 GB into a repo root **[F]**, unreadable without driver symbols.

### 2.2 A dead process is not a released process

**[M/F]** An exception escaping `main` does **not** reliably end a multi-device job: normal
interpreter shutdown joins the PJRT worker threads, and a thread parked in a rendezvous never
joins. A run that "crashed" can hold every GPU indefinitely. Exit hard:

```python
def run_entrypoint(main):
    try:
        main()
    except BaseException:
        traceback.print_exc()
        sys.stderr.flush(); sys.stdout.flush()
        os._exit(1)          # sys.exit() would block joining a parked PJRT thread
```

### 2.3 Detecting a hang: the only signal that does not lie

| signal | verdict |
|---|---|
| process exists | **useless** — a hung job lives forever |
| exit code | **useless** — never arrives |
| GPU memory allocated | **useless** — a hung job holds it all |
| GPU utilisation snapshot | **useless** — a healthy train loop reads 0% between steps |
| metrics-file mtime | **misleading** — healthy runs batch writes and can look 80+ min stale |
| **CPU-tick delta** | **reliable** — `/proc/<pid>/stat` fields 14+15 (utime+stime) |

**[F]** A hung process burned ~1 tick per 15 s with both GPUs at 0% util while still holding
165 GB and 131 GB; a healthy trainer burns thousands in the same window. The regimes are three
orders of magnitude apart, so the threshold is not delicate.

Three properties a watchdog needs that the tick delta alone does not give you:

- **Debounce.** Require several *consecutive* quiet polls (e.g. 40 × 15 s). One quiet poll is a
  long checkpoint write or a host-side pause, not a hang.
- **A startup grace period.** Shuffle-buffer fill plus compilation can exceed 20 minutes; a
  watchdog armed at t=0 kills healthy launches.
- **A fast-failure cap.** A death inside the grace period is a launch failure (bad config, OOM at
  step 1), not a stall. Stop relaunching after a few.

**Prefer an in-process heartbeat to an external prober.** A daemon thread that watches a
`beat(position)` timestamp knows *where* the loop was, and can `os._exit()` — releasing the GPUs
even though a PJRT thread will never join. Layer it: (1) the XLA termination flag for rendezvous
stalls, (2) the heartbeat watchdog for every other stall, (3) the hard-exit entrypoint of §2.2.

**Before you kill a hung run, ask it where it is.** Register
`faulthandler.register(signal.SIGUSR1, all_threads=True, chain=False)` at startup; then
`kill -USR1 <pid>` dumps every thread's stack to stderr without killing the process. That dump is
usually the *only* record of where a hang was. (`chain=False` matters: chaining re-raises to the
default handler, which terminates.)

### 2.4 Multi-process adds a heartbeat — but not a cure

If you run multi-process, `jax.distributed` does *"health checking, ensuring that all processes
shut down if any process dies"* **[C]**. Read the default carefully anyway — JAX's
[fault tolerance](https://docs.jax.dev/en/latest/fault_tolerance.html) page **[C]**:

> *"By default, if a process fails while participating in a distributed computation (like
> `jnp.sum`), then the rest of the processes participating in the computation will get stuck
> **forever**."*

Heartbeats fate-share the *processes*; they do not unwedge an *in-flight collective*. You still
want §2.1. The knob is `heartbeat_timeout_seconds` (default 100) — not `heartbeat_timeout`
**[M]** — and the survivors' fatal message carries the most useful operational hint in the stack:
*"Disable Python buffering, i.e. `python -u`, to be sure to see all the previous output"* **[C]**.
Without `-u` the dying process's traceback, the only thing that says *why*, is lost unflushed.

Prevention beats detection: *"it's crucial that all processes… run the same computation in the
same order… beware of any control flow that depends on `jax.process_index()` and includes
communication"* **[C]**. `multihost_utils.assert_equal` on shapes/step counters/config hash before
entering a `jit`, plus named `sync_global_devices` barriers to bisect divergence, is the documented
mismatch check. **Single-process `pmap` on local devices gets none of this** — hence §2.1–2.3.

For the full API, the coordinator's own error strings, live inspection of a wedged job (NCCL RAS
on `localhost:28028`, `gdb thread apply all bt`, profiler TraceMe stall counts, per-rank HLO
diffing) and what upstream issues actually say, see
**`references/collective-hang-toolkit.md`**.

---

## 3. Scaling a recipe without changing the experiment

### Every step-counted quantity must be divided

If a step consumes N times the samples, **everything counted in steps reaches its boundary on
N times the data**. Halving two of three is worse than halving none, because the arm looks subtly
wrong rather than obviously wrong.

```
steps_per_epoch                    ÷ N
unfreeze/freeze schedules          ÷ N
lr_decay_updates / cosine horizon  ÷ N     <-- the one that gets missed
warmup_steps                       ÷ N (usually)
eval/checkpoint cadences           ÷ N (if you want them at the same data volume)
```

Missing the LR horizon means the schedule completes on N× the data, so at any matched sample
count the arm sits at a **higher** LR — less decayed *and* often a scaled-up peak. It presents as
"multi-GPU is mysteriously less sample-efficient".

**Verify from the run's own effective config, not the launch flags.** Whether a resume honours a
config file is a property of *your* trainer — many rebuild config from the checkpoint and re-apply
only a whitelist of CLI overrides, so a passed `--config` is silently ignored. Read the value the
process logs at startup (or logs to your experiment tracker), never the command line.

### Divisibility is a hard startup gate

Every batch bucket's `B` must divide the device count — **including eval buckets**, which are easy
to forget and fail only at startup on the larger device count.

### Decide whether sharding pays before you build for it

Two numbers settle it, and neither is throughput.

**Critical batch size.** Above it, more parallelism buys wall-clock and *loses* sample efficiency.
If your critical batch fits on one device, more devices cannot help — and if data is your binding
constraint rather than time, going past it is strictly bad.

The standard model is McCandlish, Kaplan & Amodei, *An Empirical Model of Large-Batch Training*
([arXiv:1812.06162](https://arxiv.org/abs/1812.06162)) **[C]**. Its printed tradeoff law is
`(S/S_min − 1)·(E/E_min − 1) = 1` with `B_crit ≡ E_min/S_min`, equivalently (Appendix D, fixed
batch) the more usable `S/S_min = 1 + B_crit/B` and `E/E_min = 1 + B/B_crit`. At exactly
`B = B_crit` you pay **2× the minimum steps *and* 2× the minimum data** — a turning point, not a
free lunch. Two conditions a naive fit violates **[C]**: **re-tune the LR at every batch size**
before fitting (and fit in log space), and remember `B_crit` *"typically increases by an order of
magnitude or more over the course of training"* — so it exists only relative to a stated
performance target.

**You can measure it instead of fitting it, almost for free.** The gradient-noise estimator needs
only the gradient norm **before and after** the cross-device average **[C]**:

```
S ≡ (|G_small|² − |G_big|²) / (1/B_small − 1/B_big)      # B_small = per-device, B_big = global
```

— *"we can compute these with minimal effort by computing the norm of gradient before and after
averaging between devices."* Two extra scalars in a `pmap`/`shard_map` step, and you get `B_crit`
from one run instead of a sweep. Say **measured** if you did this and **curve fit** if you fitted
the tradeoff law to (arm, target) observations; they are different claims.

**Learning rate does not scale with a single rule** — it scales with an exponent that depends on
the optimizer, in the *saturating* form `ε(B) = ε*/(1 + B*/B)^α`: `α = 1` (linear) for
SGD/momentum, `0.5 < α < 1` for Adam/RMSProp, `α = 0.5` for the classic variance-preserving √ rule
**[C]**. Because it saturates, an unbounded `lr *= sqrt(ratio)` overshoots at large `B`. Warmup is
not optional and should be **gradual**, because *"the linear scaling rule breaks down when the
network is changing rapidly, which commonly occurs in early stages of training"* **[C]**. The
largest study of this (Shallue et al., 35 workloads) found the optimum *"did not always follow
either a linear or square root scaling heuristic"* and that LR and momentum must be tuned
**jointly** **[C]** — so treat the rule as a starting point for a re-tune, never as a substitute.

**Two traps around the comparison itself** **[C]**:

- **The budget is not neutral.** An epoch/example budget only ever probes the perfect-scaling
  regime and favours small batches; a step budget favours large ones. Say which you used.
- **Check you are not simply IO-bound first.** [Tuning
  Playbook](https://github.com/google-research/tuning_playbook): *"if the batch size doubles, the
  training throughput should also double… If this is not the case then the training pipeline has a
  bottleneck such as I/O or synchronization between compute nodes."* Its usual conclusion is worth
  hearing before you build anything: *"the largest batch size supported by the available hardware
  will be smaller than the critical batch size… a good rule of thumb is to use the largest batch
  size possible."* (Gradient accumulation buys none of this — it *"does not provide any throughput
  benefits"*.)

Citations, exact equations and the recent CBS literature: **`references/scaling-and-batch-size.md`**.

**Decompose any speedup you quote.** "2 GPUs gave 1.71×" is usually two changes at once — the
extra devices *and* a bigger batch. Measure the batch increase on **one** device first:

```
1.71  =  2 (the doubled batch)  /  1.16 (the sharding tax)
```

**[F]** That decomposition showed the second device contributed a 16% *overhead* and nothing else,
and that the whole useful batch range fitted on a single card. Comparing an N-GPU arm at batch 2B
against a 1-GPU arm at batch B measures the batch, not the hardware.

### An N-GPU arm is not the same objective as a 1-GPU arm

- **Masked means.** Gradients are `pmean`'d, but a loss term computed as `sum / max(count,1)`
  makes mean-of-per-device-means ≠ global masked mean whenever counts differ across shards.
- **Percentiles are wrong.** A `pmean` over per-device percentiles is not a global percentile.
  Means are fine; treat `p50`/`p90`/`p99` as approximate.
- **Contrastive losses change meaning.** Gathering across devices changes the negative-pool size,
  which changes the objective. Check whether your resume path force-enables such a gather — resume
  and fresh launch then optimise different things.
- **The random stream is not device-count invariant.** The standard idiom derives a per-device key
  inside the mapped function, `fold_in(rng, step)` then `fold_in(step_key, lax.axis_index(...))`
  (`axis_index` is free — it lowers to `ReplicaId` plus arithmetic, no communication **[C]**). It
  is reproducible at a **fixed** device count and *not* across a change in device count, so a
  2-GPU and a 4-GPU arm see different augmentation/dropout noise even at matched global batch.
  Note this is community practice: **no official JAX page documents PRNG handling across devices**
  **[C, negative]**. Two rules regardless: init must use an *identical* key on every device or the
  replicas diverge on step 0; dropout/augmentation must use a *varying* key or you lose batch
  diversity.
- **There is a noise floor even at N=1.** **[F]** Two runs of the *same* step implementation with
  identical model/state/batch/key diverged after two steps: ~4e-7 absolute on parameters, ~1e-3
  relative on losses. **Run an A-vs-A control to establish that floor before reading any small
  1-GPU-vs-N-GPU gap as signal.** [OpenXLA's determinism page](https://openxla.org/xla/determinism)
  names two GPU sources — **autotuning** picking a different winning kernel across compiles
  (pin with `--xla_gpu_autotune_level=0` or persisted AOT autotune results) and **nondeterministic
  ops** accumulating via atomics — and offers `--xla_gpu_exclude_nondeterministic_ops` at
  *"substantial runtime throughput loss"*, which hard-fails compilation for ops with no
  deterministic lowering **[C]**. `--xla_gpu_deterministic_ops` also exists in the plugin **[M]**
  but is absent from that page **[C, negative]**.
- **Do not say "NCCL is nondeterministic".** The reduction tree is fixed at communicator init, so
  an all-reduce is generally run-to-run reproducible on an *unchanged* configuration; what it is
  not is **invariant to configuration** — change the device count, rank order, algorithm, protocol
  or message size and float non-associativity gives you different bits **[C, inferred from NCCL
  issue reports; no NVIDIA guarantee found]**. For 2-GPU vs 4-GPU that is the operative statement:
  the arms are not bitwise comparable even with identical seeds and data order.

---

## 4. Instruments and knobs that behave differently on several devices

### Buffer donation matches on the *sharded* aval

Donation (`jax.jit(donate_argnums=...)`, `eqx.filter_jit(donate=...)`) aliases an input buffer to
an output of the same shape and dtype. On several devices the match is made on the **per-device
shard**, not the global shape **[C, read from `jax/_src/interpreters/mlir.py`]**. Consequences
that produce no error at all:

- Same global shape but a **different sharding** → different shard shapes → **no aliasing**, no
  memory saving, only `UserWarning: Some donated buffers were not usable: …`.
- **Memory kinds must match** (`device` vs `pinned_host`); the source comment is explicit that
  cross-memory donation is not supported yet.
- An `AUTO`-layout input donated toward a concrete-layout output **raises**.
- Keyword arguments are never donated — `f(params=p)` silently donates nothing **[C]**.
- `jit` + `shard_map` + `donate_argnums` was genuinely broken until jax 0.4.23
  ([jax#15368](https://github.com/jax-ml/jax/issues/15368), fixed 2024-02) **[C]**.

Because every one of these degrades to a *warning*, promote it in CI:
`warnings.filterwarnings("error", message="Some donated buffers")`. Otherwise a sharding change
silently removes an optimisation you are still budgeting memory for.

### Catch accidental host round-trips with the transfer guard

[`jax.transfer_guard`](https://docs.jax.dev/en/latest/transfer_guard.html) **[C]** takes
`allow` / `log` / `disallow` / `log_explicit` / `disallow_explicit`, plus directional variants
(`jax_transfer_guard_host_to_device`, `_device_to_device`, `_device_to_host`). Two properties make
it the right tool here:

- **`"disallow"` blocks only *implicit* transfers** — a stray `float(loss)`, `print(array)` or
  `np.asarray(x)` inside the step — while still allowing explicit `device_put`/`device_get`, so
  checkpointing keeps working. Use `disallow_explicit` only for the innermost loop.
- The error names the **destination sharding**, which is exactly what you want when diagnosing
  placement **[M]**:
  `INVALID_ARGUMENT: Disallowed host-to-device transfer: aval=…, dst_sharding=SingleDeviceSharding(…)`

**Caveat [C]:** the context manager is thread-local and *"a newly spawned thread will use the
global option"* — a guard set in the training thread does not cover a background prefetch thread.
Set the global flag if you mean the whole process.

### `jax.debug.print` is not free on several devices

Under `pjit`/sharded `jit`, *"a global synchronization occurs that will materialize values on a
single device"*; under `pmap` the prints *"might be reordered"* and `ordered=True` **raises**
**[C]**. A debug print left in a sharded step costs a device-wide sync every step. (A plain Python
`print` under `jit` is free precisely because it only runs at trace time.)

### Profiling

`jax.profiler.trace("/tmp/prof")` around a **`block_until_ready()`'d** call — the doc is explicit
that without it async dispatch ends the trace before the work runs **[C]**. For a job already
running, `jax.profiler.start_server(9999)` plus `python -m jax.collect_profile <port> <ms>` (or
XProf's capture-by-address) beats restarting it. The TensorBoard plugin is now `xprof`; **HLO Op
Stats** and the **trace viewer** are where all-reduce/all-gather time actually shows up.
**Negative finding [C]:** the JAX profiling page contains *no* multi-process guidance at all —
single-host multi-GPU is covered (each local device is its own row), multi-process is not, and you
fall back to per-process capture.

### Knobs upstream actually recommends

From [GPU performance tips](https://docs.jax.dev/en/latest/gpu_performance_tips.html) **[C]**:

- Single-host multi-GPU NCCL tuning: `NCCL_LL128_BUFFSIZE=-2`, `NCCL_LL_BUFFSIZE=-2`,
  `NCCL_PROTO=SIMPLE,LL,LL128` — intra-node only, *"don't seem useful for multi-host
  communication yet"*.
- `--xla_gpu_enable_latency_hiding_scheduler` (default off) to overlap collectives with compute.
  It changes the live-range structure, so re-check peak memory when you flip it.
- Collective **combiner thresholds** default to 256 bytes and should be raised
  *"high enough so as to combine at least a Transformer Layer's weight"*:
  `--xla_gpu_all_gather_combine_threshold_bytes`,
  `--xla_gpu_reduce_scatter_combine_threshold_bytes`,
  `--xla_gpu_all_reduce_combine_threshold_bytes`.
- Multi-process: **one process per GPU**, not one per node.

### `multihost_utils` is for multi-*process*, not multi-*device*

`jax.experimental.multihost_utils` (`sync_global_devices`, `process_allgather`,
`broadcast_one_to_all`, `assert_equal`, `host_local_array_to_global_array`) is *"Utilities for
synchronizing and communication across multiple hosts"* **[C]**. On a single-host box with several
GPUs `jax.process_count() == 1`, every device is local, and none of it is needed — reaching for it
there is a common cargo-cult. When you *are* multi-process, `assert_equal` and
`sync_global_devices` are the cheap way to catch the mismatched-collective class of hang (processes
disagreeing about what to call, or in what order) before it becomes a rendezvous stall.

---

## 5. Operational habits that pay for themselves

- **Never mutate a venv while runs are live.** Replacing a package unlinks shared objects the
  running processes have mmap'd; they die silently, staggered, with no diagnostic. Clone the venv,
  mutate the clone, launch new runs against it.
- **Never kill by pattern.** `pgrep -f <name>` matches your own command line, and on a shared box
  a name match can take out someone else's job. Resolve explicit PIDs (`ps -eo pid,args`), then
  signal those.
- **Stagger launches.** Two simultaneous XLA compilations of a large program can push load high
  enough that something gets killed with no traceback. Start one, let it compile, then the next.
- **Budget the cold start.** Shuffle-buffer fill plus multi-device compilation can take 15–25
  minutes before the first step **[F]**. Judging a launch at 20 minutes has twice produced a false
  "it hangs".
- **Some warnings are permanent noise.** `VMM cuMemCreate with FABRIC+POSIX_FD …
  CUDA_ERROR_NOT_PERMITTED` appears on every multi-GPU start under container capability limits and
  falls back automatically **[F]**. Confirm collectives work (`psum` + a large all-reduce) once,
  then stop reading it. (`Some donated buffers were not usable` is *not* in this category — see §4.)
- **Grep for the mechanism, not the string.** Command-buffer formation is a *thunk-level* pass:
  optimized HLO contains `command_buffer` zero times even when buffers are being built **[F]**. Use
  `TF_CPP_VMODULE=command_buffer_conversion_pass=3`.
- **Checkpoint atomically.** Stage every member to `.tmp` and rename, **metadata last**, so
  "metadata exists" implies a complete set. A non-atomic writer with `keep_last=1` has a window
  (measured at 23–43 s on 12 GB checkpoints **[F]**) in which a death leaves *zero* resumable
  checkpoints.

---

## Quick reference

| Symptom | Likely cause | Section |
|---|---|---|
| Alive, 0% util, no metrics, holds GPUs | collective hang after a replica died | §2 |
| `Acquire clique` / `rendezvous.cc` / `Expected N threads to join` | same | §2 |
| Hung job survives a crash and keeps its GPUs | PJRT thread never joins at shutdown | §2.2 |
| `Received incompatible devices for jitted computation` | one operand pinned, one still replicated | §1.3 |
| Huge OOM at checkpoint/validation boundary | unreplication residency ate the margin | §1 |
| `requested by op ` with a blank name | not attributable — read the code, don't rerun | §1.7 |
| Error blames a jit'd fn that has no such op | async attribution at the next sync point | §1.7 |
| Request size varies by model/loss config | it is a computation's workspace, not a copy | §1.7 |
| Smaller `MEM_FRACTION` makes it fail *sooner* | margin problem, not a leak in that request | §1.7 |
| Ported off `pmap` and the numbers changed | `x[0]` on a replicated (not stacked) array | §1.4 |
| `AttributeError: device_put_replicated` | removed in jax 0.10 — build an explicit mesh | §0 |
| `Unknown flag in XLA_FLAGS` at first device use | the flag name does not exist | §2.1 |
| `Check failed: tsl::Flags::Parse … usage: --foo=BAR` | the flag exists; the VALUE is malformed | §2.1 |
| Warning says "unstuck … false-positive" | straggler, not a hang — raise the *warn* timeout | §2.1 |
| `ShardingTypeError … out sharding could not be resolved` | `x[0]` on an Explicit-mode mesh | §1.4 |
| `NCCL_TIMEOUT` etc. had no effect | PyTorch variables, absent from NCCL | §2.1 |
| N-GPU arm less sample-efficient than 1-GPU | a step-counted schedule was not divided | §3 |
| Startup: batch not divisible by device count | eval bucket, usually | §3 |
| Runs die silently just after a package change | venv mutated under live processes | §5 |
| `Some donated buffers were not usable` on a sharded jit | donation matched on shard shape, not global shape | §4 |
| A sharded step got slow after adding a debug print | `jax.debug.print` forces a global sync | §4 |

## Pre-flight checklist before launching on N devices

- [ ] Every unreplication goes through one helper that `device_put`s to a device — no bare `x[0]`
- [ ] That helper guards non-array and 0-d leaves
- [ ] A test asserts single-device placement **and** total resident bytes across a save cycle
- [ ] `steps_per_epoch`, LR horizon, warmup and freeze/unfreeze schedules all divided by N
- [ ] Every batch bucket, **including eval**, is divisible by N
- [ ] Timeouts armed for the rendezvous you can actually hit, set before `jax` is imported and
      echoed in the log (`--xla_gpu_nccl_termination_timeout_seconds`,
      `--xla_gpu_execution_terminate_timeout`)
- [ ] Every new `XLA_FLAGS` entry smoke-tested against a one-line program that touches a device
- [ ] `RLIMIT_CORE` dropped to 0; `faulthandler` on SIGUSR1
- [ ] Heartbeat watchdog with debounce + startup grace + fast-failure cap; entrypoint `os._exit`s
- [ ] Checkpoints written atomically, metadata last
- [ ] The speedup you plan to quote is decomposed into batch effect vs sharding tax
- [ ] Critical-batch estimate says another device can help at all

## Related skills

- `jax-memory-and-retracing` — the single-device half of the memory story: retrace leaks, host-RAM
  OOM, allocator diagnosis. Read it first if the OOM is not at a checkpoint/validation boundary.
- `jax-jit-and-fusion` — jit boundaries, `donate_argnums`, and honest warm/`block_until_ready`
  benchmarking, which §3's speedup decomposition depends on.
- `jax-config` — static/dynamic config separation, so the schedule constants in §3 have one source
  of truth to divide.

## References

- `references/collective-hang-toolkit.md` — the full XLA timeout-flag table with defaults and
  verbatim help strings, the flag-naming traps, real vs PyTorch NCCL variables, NCCL RAS,
  `jax.distributed` failure semantics, and how to inspect a job that is wedged right now.
- `references/scaling-and-batch-size.md` — critical-batch-size and LR-scaling literature with exact
  equations, the caveats that invalidate a naive fit, and recent work on how CBS actually scales.
