# Collective-Hang Toolkit: XLA flags, NCCL variables, and live inspection

Companion reference for `jax-multi-gpu` §2. Evidence tags as in the skill: **[M]** measured on
jax/jaxlib 0.10.1 with the CUDA plugin, **[C]** cited from upstream docs/source, **[F]** field
report from one project.

---

## 1. Read the rendezvous NAME, then pick the flag that arms it

The stall message is emitted by one function (`xla/service/rendezvous.cc`
`AwaitAndLogIfStuck`) for **four different rendezvous points**, each with its own pair of
timeouts. The `%s` in the message is the rendezvous name, and it is the whole triage **[C]**:

| name in the log | warn / terminate flags | defaults |
|---|---|---|
| `Acquire clique: …` / `Initialize clique: …` | warn hard-coded 10 s · `--xla_gpu_nccl_termination_timeout_seconds` | **−1 = never terminate** |
| `first call … collective operation: kind=…` | `--xla_gpu_first_collective_call_warn_stuck_timeout_seconds` · `…_terminate_timeout_seconds` | 20 · 40 |
| `thunk initialization completion for device ordinal …` | `--xla_gpu_executable_warn_stuck_timeout` · `--xla_gpu_executable_terminate_timeout` | 10 · 30 |
| whole-execution deadlock (no rendezvous) | `--xla_gpu_execution_terminate_timeout` | **`inf`** |

So an `Acquire clique` hang lasts forever by default, while a first-collective-call hang already
self-terminates after 40 s. **[F]** That is why, on an `Acquire clique` stall, only
`--xla_gpu_nccl_termination_timeout_seconds=N` ended the process and the other `*_terminate_*`
flags appeared to "do nothing" — they were arming rendezvous the job never reached. Match the flag
to the name in the log; do not bisect the family.

Related and worth setting at the same time **[C]**:

- `--xla_gpu_nccl_terminate_on_error` (default `false`) — *"If set, then NCCL errors will
  terminate the process."*
- `--xla_gpu_execution_terminate_timeout` — the actual whole-execution watchdog. XLA's own comment:
  *"If XLA:GPU executable doesn't complete its execution within some reasonable time frame it
  probably means that it deadlocked in one of the GPU kernels or collective communication. It is
  nearly impossible to recover from such deadlock…"* Default `inf`, so it is off until you set it.
  Pair with `--xla_gpu_execution_progress_tracking=16` to get the last N thunks named.

**The terminate timeout is not just a killer — it dumps every thread's stack.** `rendezvous.cc`
calls `DumpAllThreadStacksToLog()` immediately before its `LOG(FATAL)` **[C]**. That dump
(`All thread stack traces (if supported on this platform):`) is the single best artefact for a
collective hang and is easy to scroll past. It is also why `--xla_gpu_execution_terminate_timeout`
beats an external `kill`: the external kill gets you nothing.

**Do not treat every stuck warning as a bug.** The same code emits a recovery line **[C]**:

> *"This thread is unstuck waiting for `…` after …. Threads joined rendezvous with significant
> delay, system can be overloaded… Warning above was a false-positive. Perhaps the timeout is too
> short."*

Uneven per-device work under `pmap` produces exactly this. If you see it, **raise** the warn
timeout rather than chase a hang.

#### A working flag set

```bash
export XLA_FLAGS="\
--xla_gpu_nccl_termination_timeout_seconds=600 \
--xla_gpu_execution_terminate_timeout=10m \
--xla_gpu_execution_progress_tracking=16 \
--xla_gpu_executable_warn_stuck_timeout=60 \
--xla_gpu_executable_terminate_timeout=600 \
--xla_gpu_first_collective_call_warn_stuck_timeout_seconds=60 \
--xla_gpu_first_collective_call_terminate_timeout_seconds=600"
```

**[M]** This exact string parses on jaxlib 0.10.1.

#### Two naming traps that will kill your job at startup

XLA exact-matches flag names, and **anything it does not like is fatal at first backend init** —
a single `F…` line that looks nothing like a Python traceback and gets misread as a driver fault.
The two failure signatures are different and tell you different things **[M]**:

| what you see | what it means |
|---|---|
| `parse_flags_from_env.cc:234] Unknown flag in XLA_FLAGS: --foo` | **the flag does not exist** |
| `parse_flags_from_env.cc:220] Check failed: tsl::Flags::Parse … usage: --foo=BAR` | the flag exists; **the VALUE is malformed** |

Both traps are live in this family:

- **`--xla_gpu_execution_terminate_timeout` takes a DURATION STRING, not a number.** `=10m` and
  `=600s` parse; `=60` fails with the *second* signature above **[M]**. Reading that failure as
  "not a flag" is an easy and expensive mistake — it discards the one flag whose stated purpose is
  *"to prevent undetected deadlocks"*. Valid suffixes: `ns us ms s m h`.
- **`_seconds` is present on some names in this family and absent on others.** Real:
  `--xla_gpu_executable_warn_stuck_timeout`, `--xla_gpu_executable_terminate_timeout`. Not real:
  the same names with `_seconds` **[M]** — which is exactly what the most-cited JAX discussion on
  this warning recommends **[C]**. Meanwhile `--xla_gpu_first_collective_call_*_timeout_seconds`
  and `--xla_gpu_nccl_termination_timeout_seconds` **do** carry it.
- There is **no** `xla_gpu_experimental_*` collective watchdog or timeout flag **[C]** — the
  `xla_gpu_experimental_*collective*` names that exist are all scheduling/perf knobs.

Always smoke-test a new flag with a one-line program that touches a device before putting it in a
launch script.

#### NCCL environment variables: mostly copy-pasted from PyTorch

**`NCCL_TIMEOUT`, `NCCL_ASYNC_ERROR_HANDLING` and `NCCL_BLOCKING_WAIT` are not NCCL variables.**
They are `torch.distributed`'s (since renamed `TORCH_NCCL_*`), they appear nowhere in NCCL's
documented 122-variable list **[C]**, and zero of the three occur in the bundled `libnccl.so.2`
(2.29.7) **[M]**. In a JAX job they do nothing at all.

What actually helps **[C]**, all present in the shipped library **[M]**:

```bash
export NCCL_DEBUG=INFO
export NCCL_DEBUG_SUBSYS=INIT,COLL,NET,GRAPH,BOOTSTRAP
export NCCL_DEBUG_FILE=/tmp/nccl/nccl-%h-%p.log   # %h host, %p pid — else N ranks interleave
```

`NCCL_LAUNCH_RACE_FATAL=1` turns a detected collective-launch-order race into an immediate error
instead of a hang **[C]**. `NCCL_PROTO=SIMPLE` is a bisection step, not a fix.

**NCCL ≥ 2.24 ships its own watchdog (RAS), on by default** — and it is the only thing in the
stack that will tell you a *mismatch* rather than just "stuck" **[C]**:

```bash
echo status | nc localhost 28028      # NCCL_RAS_ADDR default; NCCL_RAS_ENABLE defaults to 1
```

It reports per-communicator `RUNNING` / `INIT` / `MISMATCH` (*"Communicator ranks have different
collective operation counts"*) / `INCOMPLETE` / `TIMEOUT`. Query it twice: unchanged collective
counts means genuinely stuck. This works on a live wedged job without killing it.

**When to set the XLA flags.** `XLA_FLAGS` is parsed **once, at the first XLA backend
initialisation** — *not* at `import jax` **[M]**: with a bogus flag set, `import jax` succeeds and
the abort only comes when the first array touches a device. Setting it before importing `jax` is
still the right rule (it is the only point guaranteed to precede plugin init), but when auditing
whether a guard is armed, check the *program's own log of its effective `XLA_FLAGS`*, not the
import order. Also **drop `RLIMIT_CORE` to 0** first — the abort writes a core dump, one measured
at 17.5 GB into a repo root **[F]**, carrying nothing readable without driver symbols.

---

## 2. Multi-process: the coordinator already has a heartbeat

**[C]** `jax.distributed`'s stated job includes *"health checking, ensuring that all processes
shut down if any process dies"*. But read the default behaviour carefully — from JAX's
[fault tolerance](https://docs.jax.dev/en/latest/fault_tolerance.html) page:

> *"By default, if a process fails while participating in a distributed computation (like
> `jnp.sum`), then the rest of the processes participating in the computation will get stuck
> **forever**."*

Heartbeats fate-share the *processes*; they do not unwedge an *in-flight collective*. So you still
want §2.1's flags. The relevant knobs, from the 0.10.1 signature **[M]**:

```
jax.distributed.initialize(coordinator_address=None, num_processes=None, process_id=None,
    local_device_ids=None, cluster_detection_method=None, initialization_timeout=300,
    heartbeat_timeout_seconds=100, shutdown_timeout_seconds=300,
    coordinator_bind_address=None, slice_index=None, partition_index=None)
```

Note it is `heartbeat_timeout_seconds`, not `heartbeat_timeout` **[M]**. When a peer dies you get
`Task <id> heartbeat timeout…` on the coordinator and, on every survivor, a `LOG(FATAL)` whose
text contains the most useful operational hint in the stack **[C]**:

> *"Terminating process because the JAX distributed service detected fatal errors… **Disable
> Python buffering, i.e. `python -u`**, to be sure to see all the previous output."*

Without `-u`, the dying process's traceback — the only thing that says *why* — is frequently lost
in an unflushed stdout. Also worth knowing: **if process 0 dies, everything dies**, because it
hosts the coordination service; fault tolerance is documented as *"still experimental… probably
buggy"*; and the opt-in recovery path is `jax.config.update("jax_enable_recoverability", True)`
plus `multihost_utils.live_devices` **[C]** (both present in 0.10.1 **[M]**).

**Prevention beats detection here.** The multi-process doc is blunt **[C]**: *"it's crucial that
all processes with participating devices run the same computation in the same order… the easiest
way to avoid deadlocks is to run the same Python code on every process, and beware of any control
flow that depends on `jax.process_index()` and includes communication."* `multihost_utils`
`assert_equal` (*"Verifies that all the hosts have the same tree of values"*) on shapes, step
counters and a config hash before entering a `jit`, plus named `sync_global_devices` barriers to
bisect where they diverge, is the documented mismatch check.

**Single-process `pmap` on local devices gets none of this** — hence §2.1–2.3.

---

## 3. When you still have to look inside

In rough order of cost:

1. **Let the terminate timeout fire** (§2.1) and read `DumpAllThreadStacksToLog`'s output.
2. **Ask NCCL RAS** — `echo status | nc localhost 28028` — for `MISMATCH` / stuck collective
   counts, without killing the job **[C]**.
3. **`kill -USR1`** for the Python-side stacks (§2.3).
4. **Profile it while it hangs.** `rendezvous.cc` emits TraceMe annotations naming the stall —
   `Wait: pending_threads=%d/%d`, `Wait for rendezvous callback`, `Stuck Waiting for %d of %d`
   **[C]** — so a trace captured *during* the hang gives you arrived/expected counts directly.
   `jax.profiler.start_server(9999)` in the process, then
   `python -m jax.collect_profile <port> <ms>`.
5. **`gdb -p <pid> -batch -ex "thread apply all bt"`** — the maintainer-endorsed last resort on
   the long-standing "multi-GPU randomly hangs forever" reports **[C]**.
6. **Diff the per-rank HLO.** `XLA_FLAGS="--xla_dump_to=/tmp/xla_dump/rank$RANK"`; a genuine
   mismatch shows as differing collective ops / `replica_groups` / `channel_id`. Note the negative:
   identical dumps do **not** rule out a hang — there is at least one open report of a hang in
   *compilation* rather than in the collective **[C]**.
7. `TF_CPP_MIN_LOG_LEVEL=0` plus
   `TF_CPP_VMODULE=gpu_cliques=3,rendezvous=3,collective_thunk=3` for XLA's own verbose logging
   **[M for the env vars; C for the module keys]**.

**Upstream has no cure, only detectors.** Reviewing the open JAX issues on these exact strings:
several are years old with no maintainer root-cause, and the recurring advice is (a) raise the
timeouts if it is a straggler false-positive, (b) capture thread stacks, (c) upgrade NCCL **[C]**.
Do not expect to find a flag that makes the hang not happen.

---
