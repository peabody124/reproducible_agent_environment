# ~80% ASD-STE100 Starter Templates

Copy and adapt these starter templates when creating `docs/SPEC.md`, `docs/specs/00_overview.md`, or `docs/papers/<paper_slug>/SPEC.md`.

---

## 1. Single Unified Repository Spec (`docs/SPEC.md`)

```markdown
# Technical Specification: <Project Name>

> **Format:** ~80% ASD-STE100 (Active voice; <= 20 words per procedural step; <= 25 words per descriptive sentence; explicit shapes, frames, and units).
> **Code Anchor Commit:** `<git-sha>`

## 1. Purpose and Scope
- **System Actor:** `<package_name>` (`src/<package_name>/`)
- **Primary Function:** `<package_name>` estimates <target quantities> from <input modalities> for <target cohort/application>.
- **Out of Scope:** `<package_name>` does not perform <upstream/downstream task>; `<external_repo>` handles that stage.

## 2. Terminology and Coordinate Conventions
| Term / Symbol | Exact Definition | Shape & Type | Frame & Units |
| :--- | :--- | :--- | :--- |
| `keypoints_2d` | Undistorted 2D image keypoint detections with confidence | `(T, C, K, 3)` `float32` | `camera_undistorted`, `px` |
| `qpos` | Generalized biomechanical joint coordinates | `(T, D)` `float32` | `world`, `rad` and `m` |

## 3. Input Contracts
1. `<entrypoint>` accepts `keypoints_2d` `(T, C, K, 3)` and calibrated `camera_params` from `<source>`.
2. `<entrypoint>` raises `ValueError` if fewer than two calibrated cameras are present.

## 4. Sequential Pipeline Stages

### Stage 1: Preprocessing (`src/<pkg>/preprocess.py`)
1. `undistort_keypoints` maps raw pixel coordinates to normalized camera rays using OpenCV pinhole intrinsics.
2. `mask_low_confidence` zeros keypoint observations with detection confidence below `0.30`.

### Stage 2: Optimization (`src/<pkg>/solver.py`)
3. `initialize_trajectory` triangulates 3D keypoints (`mm`, `world` frame) across all valid camera pairs.
4. `solve_sequence_ik` minimizes Huber 2D reprojection error plus joint acceleration penalty over `100` L-BFGS steps.

## 5. Output Contracts and Invariants
- **Primary Output:** `ReconstructionResult` containing `qpos` `(T, D)` (`rad`, `m`) and `joint_centers_3d` `(T, J, 3)` (`mm`, `world`).
- **Hard Invariants:**
  1. `qpos` contains zero `NaN` or `Inf` values.
  2. All anatomical joint angles stay within physiological range-of-motion bounds (`±1e-4 rad` tolerance).

## 6. Verification and Benchmark Gates
| Gate | Command | Pass Criterion |
| :--- | :--- | :--- |
| Unit & Parity Tests | `pytest tests/` | 100% pass, coverage >= 80% |
| Benchmark Evaluation | `python scripts/evaluate.py` | MPJPE <= `<X.X> mm` on `<dataset>` ($N = <count>$ participants) |
```

---

## 2. Multi-Spec Suite Overview (`docs/specs/00_overview.md`)

Keep `docs/specs/00_overview.md` to **$\le 35$ lines**:

```markdown
# System Specification Overview: <Project Name>

> **Format:** ~80% ASD-STE100 Modular Specification Index.

## 1. System Purpose
`<package_name>` transforms `<raw input>` into `<final output>` across `<N>` modular subsystems. Each subsystem below enforces an independent input/output tensor contract and test suite.

## 2. Subsystem Architecture and Handoff Contracts
| Spec File | Subsystem Actor | Input Contract | Output Contract |
| :--- | :--- | :--- | :--- |
| [`01_calibration.md`](01_calibration.md) | `CalibrationPipeline` | Raw checkerboard videos `(C, H, W, 3)` | `camera_params.pkl` (`mm`, OpenCV `w2c`) |
| [`02_reconstruction.md`](02_reconstruction.md) | `KinematicSolver` | `keypoints_2d` `(T, C, K, 3)` + `camera_params.pkl` | `qpos` `(T, D)` (`rad`, `m`, `world`) |
| [`03_gait_metrics.md`](03_gait_metrics.md) | `GaitAnalyzer` | `qpos` `(T, D)` at `60 Hz` | `GaitSummary` JSON (`m/s`, `deg`, `% cycle`) |

## 3. End-to-End Verification Gate
- Run `pytest tests/` to verify all subsystem contracts and cross-module handoff invariants.
```

---

## 3. Paper Technical Specification (`docs/papers/<paper_slug>/SPEC.md`)

```markdown
# Paper Specification: <Full Paper Title> (`<paper_slug>`)

> **Format:** ~80% ASD-STE100 Engineering Blueprint for [`manuscript.md`](manuscript.md).
> **Code Provenance Commit:** `<git-sha>`

## 1. Core Problem and Thesis
1. **Measurement Gap:** Commodity video pose estimators lack calibrated joint axes and physical consistency required for clinical decision-making.
2. **Core Methodological Thesis:** `<MethodName>` couples `<Component A>` with `<Component B>` to estimate `<target>` in `<units>`.
3. **Statistical Unit of Analysis:** All hypothesis tests evaluate participant-level means across $N = <count>$ participants ($df = <N-1>$).

## 2. Notation and Symbol Contract
| LaTeX Symbol | Code Variable (`file:line`) | Definition | Shape & Units |
| :--- | :--- | :--- | :--- |
| $\mathbf{q}_t$ | `qpos` (`src/<pkg>/model.py:L30`) | Generalized coordinates at frame $t$ | `(D,)` `rad` / `m` |
| $\hat{\mathbf{y}}_{t,c}$ | `proj_2d` (`src/<pkg>/camera.py:L55`) | Projected 2D keypoints in camera $c$ | `(K, 2)` `px` |

## 3. Unified Method Stages (<= 20 Words Per Step)
1. **Stage 1 (Feature Extraction):** `<Backbone>` extracts per-camera keypoint distributions from synchronized RGB frames (`<!-- CODE: src/<pkg>/detector.py:L15-L60 -->`).
2. **Stage 2 (Trajectory Optimization):** `<Solver>` minimizes negative log-likelihood and physical priors over the full trial (`<!-- CODE: src/<pkg>/solver.py:L80-L140 -->`).
3. **Inference Label-Blindness Invariant:** Test-time evaluation uses zero ground-truth mocap markers, forceplates, or per-trial bias offsets.

## 4. Primary Quantitative Claims and Evidence Anchors
| Claim ID | Section | STE-100 Claim Statement (<= 25 words) | Metric & Value ($N$, $df$) | Script & Output |
| :--- | :--- | :--- | :--- | :--- |
| **C1** | `results.md` §3.1 | `<MethodName>` reduces sagittal joint angle MAE compared to `<Baseline>`. | `<X.X ± Y.Y deg>` vs. `<A.A ± B.B deg>` ($N=12, df=11, p<0.01$) | `scripts/eval.py` -> `outputs/metrics.json` |

## 5. Ablations That Mattered
| Variant | Modification | Quantitative Impact |
| :--- | :--- | :--- |
| **Unified Method (Ours)** | Full model (Stages 1–2). | `<X.X ± Y.Y deg>` |
| **Ablation 1 (`w/o <Term>`)** | Sets `<weight> = 0.0` in `<Solver>`. | Error increases to `<Z.Z ± W.W deg>`. |

## 6. Explicit Scope Boundaries and Limitations
1. **Observability Limit:** Video kinematics alone cannot resolve internal muscle co-contraction without EMG.
2. **Cohort Limit:** Validation covers `<N>` participants in `<setting>`; home smartphone deployment requires camera auto-calibration.
3. **Compute Cost:** One `10 s` multiview trial at `60 Hz` runs in `<T> s` on one NVIDIA A100 GPU.
```
