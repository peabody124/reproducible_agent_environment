---
name: golden-test-harness
description: >
  Set up self-generating golden/parity integration tests where a config-driven test
  harness generates the golden data on first run and the golden files are .gitignored,
  not committed. Use when adding parity tests, comparison tests, integration tests, or
  golden fixtures; when deciding whether to commit golden data; or when the user says
  "generate goldens", "golden test", "parity test", "regenerate golden", "integration
  test data", or "should I commit goldens". Covers config-points-to-DataJoint-trial,
  checked-in fixture images, pytest flags, and the rare cases where vendoring goldens
  is acceptable.
---

# Golden / Parity Test Harness

## Overview

Integration and parity tests compare a port (or refactor) against a reference
(PyTorch model, prior implementation, multi-view ground truth). The reference
outputs are "golden" data. This skill codifies the **preferred** way to manage
that golden data across this environment, so every repo does it the same way.

**The one rule that matters:**

> **Golden data is *generated*, not *committed*.** A config-driven test harness
> regenerates it on demand; `tests/golden/` is `.gitignore`d. The only test
> inputs checked into git are tiny, public-domain fixtures (e.g. one image) or a
> **config that points at a DataJoint trial**.

Committing golden NPZs (or trial-derived `tests/data/`) is an anti-pattern by
default — it bloats the repo, goes stale silently, and hides which reference the
test actually depends on. Vendor goldens **only** when explicitly chosen to make
tests runnable offline, and **document that choice** (see "When committing is OK").

## Why generated, not committed

- Golden NPZs are large (component-level captures, video E2E). They bloat clones.
- A committed golden is a frozen number with no provenance — when the reference
  model changes, the test passes against a stale golden and the regression hides.
- A config that names the **trial** (DataJoint subject/session) or the **fixture
  image** makes the test's input explicit and reproducible from source.

## Preferred input sources (in order)

1. **DataJoint trial via config (ideal for E2E/integration).** The config names a
   standard test subject/session; the harness fetches synchronized video + ground
   truth from the database. Nothing trial-derived is committed. See the
   `/pose-datajoint` and `/fetching-synchronized-data` skills for query patterns.
2. **Checked-in public-domain fixture (fine for component/unit tests).** One small
   image (COCO val or similar, ~200 KB) under `tests/fixtures/`, committed. Use for
   deterministic component-level parity that must run without a database.
3. **Vendored golden NPZ (last resort, must be documented).** Only when the test
   must run with neither torch nor the database available (e.g. offline CI).

## File layout

```
tests/
├── conftest.py              # shared fixtures, flags, load-or-generate logic
├── fixtures/
│   └── test_image.png       # public-domain input — CHECKED IN (~200 KB)
├── golden/                  # .gitignored — auto-generated, NEVER committed
│   ├── component_golden.npz # per-component: encoder, decoder layers, heads
│   └── e2e_golden.npz       # E2E outputs on the configured DataJoint trial
├── test_component_parity.py # uses checked-in fixture + component golden
└── test_integration.py      # uses DataJoint trial + e2e golden (+ benchmark)
```

**Add to `.gitignore` (every repo with parity tests):**

```gitignore
tests/golden/
```

Keep a `tests/golden/.gitkeep` if you want the directory to exist on a fresh
clone, but never commit the `.npz` files themselves.

## The load-or-generate fixture pattern

The harness generates from the reference on first run, caches the NPZ, and reuses
it on subsequent reference-free runs. No standalone `generate_golden.py` that must
be remembered and run by hand.

```python
# tests/conftest.py
from pathlib import Path
import numpy as np
import pytest

GOLDEN_DIR = Path(__file__).parent / "golden"
FIXTURE_DIR = Path(__file__).parent / "fixtures"


def pytest_addoption(parser):
    parser.addoption("--run-comparison", action="store_true", default=False,
                     help="Run reference-comparison tests (generates golden if missing)")
    parser.addoption("--run-integration", action="store_true", default=False,
                     help="Run DataJoint integration tests")
    parser.addoption("--regenerate-golden", action="store_true", default=False,
                     help="Force re-generation even when the golden NPZ exists")


@pytest.fixture(scope="module")
def component_golden(request, test_image):
    """Load cached golden, or generate it from the reference (needs torch)."""
    path = GOLDEN_DIR / "component_golden.npz"
    if path.exists() and not request.config.getoption("--regenerate-golden"):
        return dict(np.load(path, allow_pickle=False))
    pytest.importorskip("torch", reason="Golden missing — run with PyTorch to generate.")
    outputs = _generate_component_golden(test_image)   # project-specific
    GOLDEN_DIR.mkdir(exist_ok=True)
    np.savez_compressed(path, **outputs)
    return outputs
```

The same shape works for `e2e_golden`, fed by an `integration_video_frames`
fixture that pulls the configured DataJoint trial.

### Behavior matrix

| Golden exists | Reference (torch) available | `--regenerate-golden` | Result |
|---|---|---|---|
| Yes | — | No | Load from disk, run comparison |
| Yes | Yes | Yes | Regenerate, save, run comparison |
| Yes | No | Yes | Skip with clear message |
| No | Yes | — | Generate, save, run comparison |
| No | No | — | **FAIL** with "run with PyTorch installed to generate" |

Never let a missing golden **silently skip** — a parity test that quietly no-ops
is worse than no test. Skip only when the reference is unavailable *and* the
golden is cached; otherwise fail loudly.

## Test marking and usage

```python
@pytest.mark.comparison
class TestComponentParity:
    def test_encoder(self, model, component_golden, test_image):
        cos = cosine_similarity(model.encode(test_image), component_golden["encoder_features"])
        assert cos > 0.9999

@pytest.mark.integration
class TestEndToEnd:
    def test_e2e(self, model, e2e_golden, integration_video_frames):
        out = model.predict(integration_video_frames[0])
        for k in ("points", "conf", "camera_poses"):
            np.testing.assert_allclose(out[k], e2e_golden[k], atol=0.01)
```

```bash
pytest tests/ --run-comparison                      # generates golden first time, caches after
pytest tests/ --run-comparison --regenerate-golden  # after the reference model changes
pytest tests/ --run-comparison --run-integration -s # full suite incl. DataJoint trial + benchmark
```

## When committing a golden IS acceptable

Only when **all** of these hold, and it is **documented in the README**:

- The test must run where neither the reference (torch) nor the database is
  available (e.g. an offline CI lane), AND
- A regeneration script/command exists and is referenced next to the data
  (e.g. a `.gitignore` comment: `# regenerate with scripts/capture_pt_stages.py`), AND
- The committed artifact is small. Large captures stay generated/`.gitignore`d
  even in this case.

If you vendor a golden, add a README note stating *why* it is committed and *how*
to regenerate it. Silent vendoring is the anti-pattern, not vendoring per se.

## Anti-patterns to flag and fix

- `git ls-files` shows committed `tests/golden/*.npz` → should be generated + ignored.
- Committed `tests/data/<subject>/…` arrays derived from a DataJoint trial → replace
  with a config that names the trial and fetches at test time.
- A parity test that `pytest.skip`s silently when the golden is missing.
- A standalone `generate_golden.py` that must be run by hand and is easy to forget —
  fold generation into the `conftest.py` load-or-generate fixture instead.

## Guards that cannot fail

A parity suite is only worth its gates. Four shapes recur, and each produces a
test that passes for the wrong reason — worse than no test, because nobody
distrusts a green one. Prove every guard by MUTATION: break what it guards,
watch it fail, revert.

- **Asserting a value against the constant it was derived from.**
  `assert jax.config.jax_default_matmul_precision == config.MATMUL_PRECISION`
  is an identity when the fixture set the flag *from* that constant — it holds
  for every value, including the wrong one. Pin the required VALUE to a literal
  in the test, and assert the constant against it, so the constant is what is
  guarded rather than its plumbing.
- **A guard conditioned on the work being incomplete.** `assert unfinished_stages()`,
  `assert len(STUBS) > 0`, "this hazard is still unwritable" — each goes inert or
  red the moment the port finishes, i.e. exactly when it starts mattering. Make the
  precondition the check's REACH, not the work remaining.
- **A set defined by subtraction, then asserted to partition.** If
  `captured = all_keys - uncaptured`, then `captured | uncaptured == all_keys` is
  true by construction and cannot fail.
- **A test whose subject never enters the assertion** — e.g. a "the port does not
  sort" test that inspects only the reference array.

See also the jit-cache hazard in `jax-memory-and-retracing`: a mutation absorbed
by a cached trace makes any of the above look proven.

## Provenance: what a stamp must cover

- **Hash the GENERATOR SOURCE into the golden**, not just the inputs, and re-check
  it on load. A golden whose recipe is unknown cannot be reproduced later. Never
  backfill a stamp after the fact — that converts an honest gap into a false claim.
- **Every file the generator READS is a recipe source**, including the config module
  it pulls constants from. A config edit that changes what a golden MEANS while its
  stamp still reads "current" is undetectable.
- **A stale or missing stamp should FAIL LOUDLY**, not silently regenerate mid-suite:
  an unattended rebuild voids every gate measured from the old numbers, and on a
  shared GPU it is an unannounced multi-GB job.
- **Pin the capture DEVICE explicitly.** `"cuda" if available else "cpu"` is ambient:
  one capture in a shell without a visible card lands on CPU, and a CPU and a CUDA
  capture differ exactly in reduction order — so one wrong-device golden makes its
  siblings' floors describe a different computation.
- **Commit the generator before trusting its output.** A generator fix left
  uncommitted while goldens are built against it leaves HEAD rejecting every golden.

## Measure the floor on every backend the suite runs on

A tolerance derived on one backend is a tolerance for that backend. Measured on one
port: the CPU arm of the same comparison was **3.5x wider** than the GPU arms, so a
GPU-only floor is too tight for a CPU run of the same suite. The same holds across
input scales — an arithmetic floor that grows with sequence length makes a constant
measured at one size a gate for that size only. Derive from an envelope over the
configurations the suite actually runs, and have the suite report which backend
produced its numbers.

## Related skills

- `/scaffold-repo` — creates the `tests/` layout and `.gitignore` (ensure `tests/golden/`).
- `/pose-datajoint`, `/fetching-synchronized-data` — fetch the configured trial for E2E goldens.
- The workspace `eqx-porting` skill (Step 6, parity tests) drives *what* to capture
  from the reference; this skill governs *how* the golden data is stored and regenerated.
