---
name: golden-reference
description: >-
  Use when building a golden-reference test that validates a 3D reconstruction (GT
  keypoints, triangulated/FK sites, pose targets) against its database source — to
  confirm the ground truth a model trains against is itself correct before blaming
  the model. Covers pulling a known trial from DataJoint, freezing a tiny golden,
  the reproject-onto-stored-2D self-consistency check, principled tolerances, and
  skip-when-DB-unavailable gating. Use when the user says "verify the GT",
  "golden reference from the database", "is the reconstruction correct", "validate
  ground truth", or "check the training targets".
---

# Golden Reference from the Database for Reconstruction Validation

## Overview

Before you tune a model to fix a localization or accuracy problem, prove the
**ground truth it trains against is correct**. A "golden reference" test pins a
known trial's reconstruction to its database source and asserts they agree. If the
GT is noisy or self-inconsistent, no model change fixes it — and a golden test
turns that invisible data bug into a red test.

This generalizes the pattern in `BiomechMammaNetEqx/tests/test_golden_accuracy.py`
and `test_mhr_fit_golden.py`: pick one well-conditioned trial, take an **oracle**
from the source (the original pipeline's 3D, or the stored DB reconstruction),
and grade your reconstruction against it with principled, separable tolerances —
gated so the suite skips cleanly when the source is unavailable.

## When to use

- Validating that GT 3D keypoints / FK sites / pose targets a model is supervised
  against actually match the DataJoint reconstruction they came from.
- Adding a regression guard so a future data-pipeline change that corrupts GT
  (wrong settings number, frame misalignment, unit error) turns a test red.
- Any "is the reconstruction right?" question where the answer must come from the
  database source, not from the model's own output.

**When NOT to use:** model-vs-model parity (use `/golden-test-harness` for storage
mechanics) or pure 2D-keypoint analysis with no 3D/reconstruction claim.

## The core idea: self-consistency via reprojection

The cheapest, strongest check needs no second model. The GT 3D and the GT 2D in a
trial were produced from the **same camera calibration**. So re-derive the 2D from
the stored 3D through the documented projection and assert it reproduces the
stored 2D on visible joints:

```
stored_2d  ?=  project( stored_3d, calibration )
```

A real trial whose 3D and 2D came from one calibration clears a sub-pixel bar. A
GT corrupted by a frame offset, a wrong-settings concatenation, or a unit error
will not. This is exactly the "oracle reprojects onto the golden 2D within N px"
gate the BiomechMammaNet Level-2 test uses to throw out internally-inconsistent
frames — turned into the primary assertion.

Conventions you MUST hold (see the consuming repo's `docs/cameras_and_coordinates.md`):
intrinsics stay `[fx, fy, cx, cy]`; 3D is **meters** in the documented frame;
projection scales **meters → mm by 1000** and flows through the camera library
(`multi_camera.analysis.camera.project_distortion`), never a hand-rolled pinhole.

## Picking the trial and the oracle

1. **Pick a known, well-conditioned trial.** Many cameras, person in view, no
   occlusion glitches. Name it as a constant (`ASB_022`, settings `137`). Document
   it in the test docstring so the input is explicit.
2. **Always pin the settings number.** In this schema `kinematic_reconstruction_settings_num=137`
   is mandatory — omitting it concatenates settings 130+137 and silently doubles /
   corrupts the data. Use `fetch(... )` not `fetch1()` when a participant may have
   multiple sessions. (See `/datajoint-biomechanics-schema`, `/pose-datajoint`.)
3. **Reuse the production loader.** Pull the trial through the repo's existing
   loader (e.g. `dataset/creation/datajoint_loader.load_recording_data`) so the
   test validates the SAME arrays the TFRecord pipeline writes — do not
   re-implement the query or the projection.
4. **Choose the oracle.** Self-consistency (reproject stored 3D → stored 2D) needs
   only the trial. A cross-pipeline oracle (original SMPL-X mesh, a second
   reconstruction) is stronger but heavier — add it as a second level if needed.

## Freeze a TINY golden, gate on DB reachability

Trim the trial to a few frames so the frozen fixture is a few KB, and gate the
real-data pull so the suite is green offline:

```python
def _datajoint_reachable() -> bool:
    try:
        import datajoint as dj
    except ImportError:
        return False
    try:
        return bool(dj.conn(reset=True).is_connected)  # reads dj.config / env at runtime
    except Exception:
        return False
```

- **DB reachable:** pull the real trial, assert consistency on it (the real
  verdict), and under `--regenerate-golden` overwrite the frozen fixture.
- **DB not reachable:** the real-trial test `pytest.skip`s with a clear reason; an
  **offline** test still runs the identical assertion against the frozen fixture.

This mirrors the `_HAS_NET / _HAS_SCENE / _READY` flags and `skipif` in
`test_golden_accuracy.py`, and the `requires_datajoint` marker convention.

### The frozen fixture

For an offline lane, freeze a **small synthetic but self-consistent** fixture
(3D sites + calibration + projected 2D, built so reprojection error is ~0). It
exercises the verification math everywhere and is safe to commit because it is
tiny and synthetic. Document in the docstring that it is synthetic and how to
refresh it from a real trial (`--regenerate-golden`). A real-trial golden stays
small (a few frames) but, if it would be large, leave it generated and
`.gitignore`d per `/golden-test-harness`.

## Principled tolerances, not rubber-stamps

Set the bar to what a CORRECT reconstruction must achieve, and let it be red if
the data is bad (the BiomechMammaNet rule: "RED at this baseline" beats a
threshold loosened to pass):

| Check | Bar | Rationale |
|---|---|---|
| Self-consistency (reproject stored 3D → 2D), float32 same-fn | median < 1e-2 px, p99 < 1 px | pure-function recompute; only round-off |
| Self-consistency from a *different* projector | a few px | distortion-model / impl differences |
| Cross-oracle 3D (rigid-aligned to source mesh) | tens of mm, per body part | cross-model shape floor |
| Visible-joint floor | ≥ ~5% joints visible | else the check is vacuous |

Always assert a **visibility floor**: a GT that hid every joint would "pass" with
zero comparisons. Report `median / p99 / max` and the visible fraction so a
regression is legible, and separate error families (raw / centroid / rigid) when
using a cross-model oracle so position vs orientation vs shape error are distinct.

## Safety: never commit secrets or large data

- NEVER read, stage, or commit `.env`, DB credentials, or a datajoint config with
  a password. Read connection config from the existing `dj.config` / env at
  runtime; hardcode nothing.
- Keep frozen fixtures small and explicitly staged. Large captures stay
  generated and `.gitignore`d.
- NEVER modify DB entries (`update1`/`delete`/`drop`) — the database is shared lab
  state (see `/datajoint-biomechanics-schema`).

## Reference implementation

`MultiviewBiomechanicalPose` `tests/dataset/test_reconstruction_golden.py`:
offline self-consistency on a frozen synthetic fixture (always runs) + a
`requires_datajoint` real-`ASB_022`-trial check that reuses
`load_recording_data`, asserts reprojection consistency, and refreshes the
fixture under `--regenerate-golden`.

## Related skills

- `/golden-test-harness` — *how* golden data is stored/regenerated (gitignore,
  load-or-generate). This skill is *what* to capture for reconstruction validation.
- `/datajoint-biomechanics-schema`, `/pose-datajoint` — schema, settings-137,
  fetch1-vs-fetch query patterns for pulling the trial.
- `/fetching-synchronized-data` — frame-aligning 2D observations with KR qpos.
- `/camera-model` — projection, intrinsics/extrinsics, mm/m conventions.
