# Testing Standards: Golden & Parity Tests

These standards govern **golden** and **parity** tests — tests that compare a port
(or refactor) against a reference (a PyTorch model, a prior implementation, or
multi-view ground truth). They sit on top of the general `python-standards.md`
testing rules. For the full mechanics and the load-or-generate fixture pattern,
use the **`/golden-test-harness`** skill; this file is the mandatory short form.

## Golden data is generated, not committed

> A config-driven harness **regenerates** golden data on demand; `tests/golden/`
> is `.gitignore`d. The only test inputs in git are tiny public-domain fixtures
> (one small image) or a **config that points at a DataJoint trial / a clip path**.

- MUST add `tests/golden/` to `.gitignore` (keep a `tests/golden/.gitkeep`).
- MUST NOT commit golden `.npz` / per-frame masks / trial-derived `tests/data/`.
  Committing a frozen number with no provenance hides regressions when the
  reference drifts — the stale golden keeps passing.
- The committed inputs are: a config naming the trial/clip + a load-or-generate
  harness, and (optionally) a **tiny derived summary** (per-frame counts / IoU
  json, kilobytes), never raw tensors or video.

## Load-or-generate, never silently skip

Fold generation into the test/conftest (no standalone `generate_golden.py` to
forget). Behaviour matrix:

| Golden cached | Reference available | Result |
|---|---|---|
| Yes | — | Load, compare |
| No | Yes | Generate, cache, compare |
| No | No | **FAIL loudly** ("run with the reference to generate") |

A parity test that `pytest.skip`s when the golden is missing is worse than no
test. Skip only when the reference is unavailable **and** the golden is cached.

## torch vs JAX run in SEPARATE processes

On these boxes importing `torch` and `jax` into the **same** process can
deadlock (futex wait, GPU idle). For any torch-vs-jax comparison or benchmark:

- The reference (torch) capture runs in its **own subprocess / capture script**
  and writes outputs + timings to a json/npz.
- The JAX test is a **separate process** that loads the cached artifact.
- Drive both from a harness that compares the saved artifacts. Never
  `import torch` inside a JAX test module.

## Assert magnitude, not just cosine

Cosine similarity is **not** sufficient parity evidence — two tensors (or two
trackers) can have high cosine yet differ in scale or placement.

- For tensors: assert magnitude/values (`np.testing.assert_allclose` with an
  explicit `atol`/`rtol`), not only `cos > 0.999`.
- For **tracking** parity: assert **per-frame object COUNT** (within an explicit
  slack) **and** per-frame best-match **MASK IoU** (with an explicit threshold,
  e.g. mean IoU ≥ 0.7 for matched objects). Box parity where relevant.
- State thresholds as named constants with a comment justifying the value.

## Measure WARM, on GPU

Performance numbers are **warm, post-JIT, steady-state**: one warmup pass, then
time. Report latency/frame, fps, and peak GPU memory; pin precision and note
bf16 vs fp16. Keep compute on the GPU. `noop`/`plan_only` with measured evidence
is a valid honest outcome; never fabricate numbers.

## Vendoring a golden is the documented last resort

Vendoring a committed golden is acceptable **only** when all hold and it is
documented in the README / next to the file:

- the test must run where neither the reference nor the database is available
  (e.g. an offline CI lane), **and**
- a regeneration script/command exists and is referenced next to the data
  (e.g. `# regenerate with scripts/capture_pt_*.py`), **and**
- the artifact is small (large captures stay generated/`.gitignore`d).

Silent vendoring is the anti-pattern — not vendoring per se. Every committed
fixture MUST carry a one-line provenance/regeneration note pointing at its
capture script.

See `/golden-test-harness` for the full harness, conftest fixtures, and the
DataJoint-trial config patterns.
