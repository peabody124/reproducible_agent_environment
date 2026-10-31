---
name: ste100-spec
description: >
  Author, audit, and maintain ~80% ASD-STE100 (Simplified Technical English) specifications and
  technical explanations for repositories (docs/SPEC.md or docs/specs/), scientific manuscripts
  (docs/papers/<slug>/SPEC.md), and PR/bug walkthroughs. Trigger when asked to "write a spec",
  "STE-100", "STE100", "Simplified Technical English", "Karpathy STE-100", "explain in STE-100",
  "create docs/SPEC.md", "paper spec", "update the spec", or when distilling a complex codebase or
  manuscript into an unambiguous, evergreen technical specification.
---

# ~80% ASD-STE100 Technical Specifications & Explanations (`ste100-spec`)

Use this skill whenever writing, auditing, or updating technical specifications (`docs/SPEC.md`, `docs/specs/*.md`, or `docs/papers/<slug>/SPEC.md`) or explaining complex codebases, algorithms, and pull requests in **~80% ASD-STE100 (Simplified Technical English)**.

> **Background (The Karpathy ~80% ASD-STE100 Pattern):**
> **ASD-STE100** is the international aerospace maintenance specification standard designed to eliminate ambiguity in safety-critical engineering documentation. Strict 100% ASD-STE100 restricts vocabulary to a ~900-word dictionary, which forces awkward circumlocutions for modern machine learning, computer vision, and biomechanics concepts.
> At **~80% strictness** (as highlighted by Andrej Karpathy), you retain exact domain-specific technical nouns and symbols (`MHR`, `SequenceIK`, `Cholesky`, `ELBO`, `float32`, `multi_camera`) while strictly enforcing **ASD-STE100 grammar, sentence-length bounds, active voice, and one-idea-per-sentence structure**. The result is dense, zero-fluff engineering prose that humans and LLMs can parse and verify at a glance.

---

## 1. Core ~80% ASD-STE100 Writing Rules

Every specification or STE-100 explanation MUST obey these six grammatical and structural constraints:

| Rule | Constraint | Why It Matters |
| :--- | :--- | :--- |
| **1. Active Voice Only** | Every sentence must name the explicit actor (`<Actor> <verb> <object>`). Passive voice (`"is computed"`, `"are filtered"`, `"was optimized"`) is forbidden. | Passive voice hides *which* module, function, or stage performs the operation. |
| **2. Strict Sentence Length Limits** | **Procedural / pipeline steps:** **$\le 20$ words** per sentence.<br>**Descriptive / conceptual context:** **$\le 25$ words** per sentence. | Short sentences prevent nested subordinate clauses and force explicit intermediate states. |
| **3. One Idea Per Sentence** | Each sentence states **one** action, invariant, or causal relationship. Split compound sentences (`"X does A while Y does B, which enables Z"`) into numbered sequential steps. | Prevents hidden assumptions and makes every sentence independently falsifiable. |
| **4. One Term Per Concept (Zero Synonym Drift)** | Pick one exact technical term for each concept and use it identically throughout the document. Never alternate synonyms for stylistic variety. | Calling the same tensor `pose`, `joint_angles`, `qpos`, and `kinematic_state` across paragraphs causes implementation bugs. |
| **5. Maximum 3-Word Noun Clusters** | Break up stacked 4+ word noun chains (`"multi-camera keypoint trajectory optimization weight"` $\to$ `"weight for multi-camera trajectory optimization"`). | Long noun clusters obscure which word modifies which noun. |
| **6. Explicit Shapes, Frames & Physical Units** | State array shapes (`(T, J, 3)`), data types (`float32`), coordinate frames (`world`, `camera`, `pelvis-root`), and physical units (`mm`, `deg`, `rad`, `N/kg`, `Hz`) inline. Strip all marketing adjectives (`"seamless"`, `"robust"`, `"cutting-edge"`, `"novel"`, `"crucially"`). | Eliminates unit/frame mismatch bugs and AI filler prose. |

### 1.1 Before vs. After Examples (AI Slop vs. ~80% ASD-STE100)

| Standard / AI-Generated Prose (Forbidden in Specs) | ~80% ASD-STE100 Specification (Required) |
| :--- | :--- |
| *"Optimization of the biomechanical trajectory is seamlessly performed across multiple views by leveraging our novel implicit representation to minimize reprojection errors alongside temporal smoothness priors."* *(26 words, passive, vague actor, marketing fluff)* | 1. `ImplicitTrajectoryNet` maps normalized timestamps $t \in [-1, 1]$ to joint angles $\mathbf{q}_t \in \mathbb{R}^{49}$ (`rad`). *(16 words)*<br>2. `ForwardKinematics` transforms $\mathbf{q}_t$ into 3D markers $\mathbf{X}_t \in \mathbb{R}^{M \times 3}$ (`mm`, world frame). *(14 words)*<br>3. `SequenceIK` minimizes the sum of robust 2D reprojection loss and joint velocity penalties using L-BFGS. *(16 words)* |
| *"When handling missing detections, a confidence threshold is applied and low-quality keypoints are masked out before triangulation occurs."* *(18 words, passive twice, unspecified threshold/shape)* | 1. `filter_keypoints` zeros 2D detections with confidence $c_{t,k} < 0.30$ in `keypoints_2d` `(T, C, K, 3)`. *(16 words)*<br>2. `triangulate_ransac` requires at least two cameras with valid detections to estimate 3D point $\mathbf{x}_{t,k}$ (`mm`). *(16 words)* |
| *"The handrim contact phase is robustly identified using kinematic heuristics and subsequently refined via an Extended Kalman Filter."* *(18 words, passive, hides exact signals)* | 1. `ContactClassifier` predicts contact probability $p_t \in [0, 1]$ from 3D wrist-to-handrim distance (`mm`) and tangential speed (`m/s`). *(18 words)*<br>2. `PhaseEKF` updates continuous propulsion phase $\phi_t \in [0, 2\pi)$ (`rad`) at `60 Hz`. *(14 words)* |

---

## 2. Architectural Decision Framework: Single Unified Spec vs. Multi-Specification Suite

Before creating specification files in a repository or paper directory, decide whether the system belongs in **one unified specification** or **a modular suite of specifications**.

### 2.1 The 3-Question Split Test

Default to **one unified specification** (`docs/SPEC.md` or `docs/papers/<slug>/SPEC.md`). Split into **multiple modular specifications** (`docs/specs/`) **if and only if at least one** of the following three conditions holds:

1. **Independent Subsystem Contracts:** Does the repository contain distinct subsystems with independent input/output contracts that can be executed and tested in isolation? *(Example: (1) offline CT anatomical atlas construction, (2) multi-GPU flow-matching training, and (3) real-time single-camera clinical inference.)*
2. **Independent Downstream Consumers:** Do external repositories or users import or invoke one subsystem without running the others? *(Example: `BodyModels` forward kinematics vs. `MultiCameraTracking` 2D-to-3D triangulation.)*
3. **Complexity & Length Ceiling:** Would a single end-to-end specification exceed **150 lines** or **40 numbered procedural steps**?

### 2.2 Decision Matrix

| System Archetype | Layout Choice | File Paths | Line & Step Budget |
| :--- | :--- | :--- | :--- |
| **Single End-to-End Pipeline or Focused Paper**<br>*(e.g., `WheelchairPropulsion`, `ProstheticComponentry`, single clinical validation or method paper)* | **Single Unified Spec** | Repo: `docs/SPEC.md`<br>Paper: `docs/papers/<slug>/SPEC.md` | **$\le 120$ lines total**<br>($\le 30$ procedural steps) |
| **Multi-Subsystem Platform or Coupled Method Suite**<br>*(e.g., `BodyModels` + `MhrFkOpt`, multi-stage training + calibration + deployment repo)* | **Modular Spec Suite + Mandatory Top-Level Overview** | `docs/specs/00_overview.md`<br>`docs/specs/01_<subsystem_a>.md`<br>`docs/specs/02_<subsystem_b>.md`<br>`docs/specs/03_<subsystem_c>.md` | `00_overview.md`: **$\le 35$ lines**<br>Each `0N_<module>.md`: **$\le 100$ lines** |

> **MANDATORY RULE FOR MULTI-SPEC SUITES (`docs/specs/00_overview.md`):**
> Never create a directory of numbered spec files without `00_overview.md`. `00_overview.md` must stay under **35 lines** and contain:
> 1. A 2-sentence system purpose statement.
> 2. A dataflow table or ASCII diagram showing the exact tensor/file handoff between `01_...`, `02_...`, and `03_...`.
> 3. Direct links to each module specification.

---

## 3. Canonical ~80% ASD-STE100 Templates

Starter templates are also available in [`references/templates.md`](references/templates.md).

### 3.1 Template A: Project / Repository Specification (`docs/SPEC.md`)

Use this structure to specify a repository's production pipeline in $\le 120$ lines:

```markdown
# Technical Specification: <Repository or System Name>

> **Format:** ~80% ASD-STE100 (Active voice; $\le 20$ words per procedural step; $\le 25$ words per descriptive sentence; explicit shapes, frames, and units).
> **Code Anchor Commit:** `<git-sha>`

## 1. Purpose and Scope
- **System Actor:** `<package_name>` (`src/<package_name>/`)
- **Primary Function:** <1–2 active-voice sentences ($\le 25$ words each) stating what the system transforms from input to output.>
- **Out of Scope:** <1 sentence ($\le 25$ words) stating what upstream/downstream systems handle.>

## 2. Terminology and Coordinate Conventions
| Term / Symbol | Exact Definition | Shape & Type | Frame & Units |
| :--- | :--- | :--- | :--- |
| `<var_name>` | <Single-meaning definition> | `(T, J, 3)` `float32` | `world`, `mm` |

## 3. Input Contracts
1. `<Entrypoint>` accepts `<input_a>` (`<shape>`, `<dtype>`, `<units>`) from `<source>`.
2. `<Entrypoint>` validates that `<precondition>` holds; otherwise `<Entrypoint>` raises `ValueError`.

## 4. Sequential Pipeline Stages
*(Every step MUST use active voice and contain $\le 20$ words.)*

### Stage 1: <Stage Name> (`src/<pkg>/<module>.py:<func>`)
1. `<Actor>` loads `<input>` and normalizes `<field>` to `<range>` (`<units>`).
2. `<Actor>` computes `<intermediate>` (`<shape>`, `<dtype>`) using `<algorithm>`.

### Stage 2: <Stage Name> (`src/<pkg>/<module>.py:<func>`)
3. `<Actor>` projects `<intermediate>` into `<target_space>` (`<shape>`, `<units>`).
4. `<Actor>` minimizes `<objective>` over `<N>` iterations with step size `<lr>`.

## 5. Output Contracts and Invariants
- **Primary Output:** `<output_name>` (`<shape>`, `<dtype>`, `<units>`).
- **Hard Invariants:**
  1. `<Tensor>` contains zero `NaN` or `Inf` values across all valid frames.
  2. `<Physical constraint>` holds within tolerance `±<tol> <units>`.

## 6. Verification and Benchmark Gates
| Gate | Command | Pass Criterion |
| :--- | :--- | :--- |
| Unit & Parity Suite | `pytest tests/` | 100% pass, coverage $\ge 80\%$ |
| Primary Benchmark | `python scripts/<eval>.py` | `<Metric>` $\le <threshold> <units>` on `<cohort>` ($N = <count>$ participants) |
```

---

### 3.2 Template B: Paper Technical Specification (`docs/papers/<paper_slug>/SPEC.md`)

Write `docs/papers/<paper_slug>/SPEC.md` **before** drafting prose in `methods.md` and `results.md`, and keep it synchronized with the code and manuscript. While the manuscript (`methods.md`, `results.md`) uses flowing pre-2026 narrative paragraphs (per `/isr-paper-writing`), `SPEC.md` provides the crisp, unambiguous ~80% STE-100 engineering blueprint that prevents symbol drift, degree-of-freedom bugs, and code-to-paper mismatches.

```markdown
# Paper Specification: <Paper Title> (`<paper_slug>`)

> **Format:** ~80% ASD-STE100 Engineering Blueprint for [`manuscript.md`](manuscript.md).
> **Code Provenance Commit:** `<git-sha>`

## 1. Core Problem and Thesis
1. **Measurement Gap:** <Active-voice sentence ($\le 25$ words) stating what clinical/biomechanical quantity existing systems fail to measure at scale.>
2. **Core Methodological Thesis:** <Active-voice sentence ($\le 25$ words) stating how our unified formulation solves this gap.>
3. **Statistical Unit of Analysis:** <State the exact independent unit, e.g., $N = 12$ participants ($df = 11$), never pooled trials or frames.>

## 2. Notation and Symbol Contract
*(Every symbol in `methods.md` and `results.md` MUST match this table without synonym drift.)*

| LaTeX Symbol | Code Variable (`file:line`) | Definition | Shape & Units |
| :--- | :--- | :--- | :--- |
| $\boldsymbol{\theta}_t$ | `qpos` (`src/model.py:L42`) | Generalized joint coordinates at frame $t$ | `(D,)` `rad` / `m` |

## 3. Unified Method Stages ($\le 20$ Words Per Step)
1. **Stage 1 (<Name>):** `<Component>` maps `<input>` to `<latent/state>` (`<!-- CODE: src/...:L10-L45 -->`).
2. **Stage 2 (<Name>):** `<Component>` predicts `<output>` by minimizing `<objective>` (`<!-- CODE: src/...:L50-L95 -->`).
3. **Inference Label-Blindness Invariant:** At test time, `<Model>` receives zero ground-truth clinical labels, forceplate signals, or per-trial bias corrections.

## 4. Primary Quantitative Claims and Evidence Anchors
| Claim ID | Manuscript Section | STE-100 Claim Statement ($\le 25$ words) | Metric & Value ($N$, $df$) | Reproduction Script & Output JSON |
| :--- | :--- | :--- | :--- | :--- |
| **C1** | `results.md` §3.1 | `<OurMethod>` reduces 3D joint error compared to `<Baseline>` on `<Cohort>`. | `<X.X ± Y.Y mm>` vs. `<A.A ± B.B mm>` ($N=12, p=0.002$) | `scripts/eval.py` $\to$ `outputs/eval.json` |

## 5. Ablations That Mattered
| Variant | What Changes Relative to Unified Method | Quantitative Effect |
| :--- | :--- | :--- |
| **Unified Method (Ours)** | Complete formulation (Stages 1–3). | `<Primary Metric>` |
| **Ablation 1 (`w/o <Component>`)** | `<Module>` removes `<term>`. | Error increases by `+<delta> <units>`. |

## 6. Explicit Scope Boundaries and Limitations
1. **Observability Limit:** `<System>` cannot observe `<unobservable quantity>` from `<modality>` alone.
2. **Cohort / Domain Limit:** Training data covers `<population>`; `<out-of-domain case>` requires `<adaptation>`.
3. **Compute Cost:** `<Hardware>` processes a `<duration>` trial in `<time>` (`<fps> Hz`).
```

---

### 3.3 Template C: Ad-Hoc ~80% STE-100 Explanation (Code, Bug, or PR Walkthrough)

When the user asks you to *"explain how X works in STE-100"*, *"summarize this PR in STE-100"*, or *"give me a Karpathy STE-100 walkthrough"*, format your response directly using this structure:

```markdown
### ~80% ASD-STE100 Walkthrough: <Topic / PR / Subsystem>

**Purpose:** <1 active-voice sentence ($\le 25$ words) stating what the code or change accomplishes.>

**Inputs:**
- `<arg_1>` (`<shape>`, `<dtype>`, `<units>`): <1-line description>

**Sequential Execution Steps ($\le 20$ words per sentence):**
1. [`<func_a>`](file:///abs/path/to/file.py#L10-L25) reads `<arg_1>` and validates `<condition>`.
2. [`<func_b>`](file:///abs/path/to/file.py#L30-L60) transforms `<state_1>` into `<state_2>` (`<shape>`, `<units>`).
3. [`<func_c>`](file:///abs/path/to/file.py#L65-L90) writes `<output>` to `<destination>`.

**Outputs & Invariants:**
- Returns `<output>` (`<shape>`, `<dtype>`, `<units>`) with invariant `<condition>`.
```

---

## 4. Evergreen Specification Maintenance Rule

Specifications in `docs/SPEC.md`, `docs/specs/*.md`, and `docs/papers/<slug>/SPEC.md` are **evergreen engineering contracts**, not historical changelogs:

1. **Same-Commit Synchronization Mandate:** Whenever a code change or manuscript revision modifies input/output shapes, coordinate conventions, pipeline stages, loss terms, degrees of freedom, or headline benchmark numbers, you **must** update the corresponding STE-100 specification in the **same commit / PR**.
2. **Never Document Historical Evolution in `SPEC.md`:** Do not write *"In v1 we used X, and in v2 we switched to Y"* inside a specification. Document **only** what the current production code does today. Leave change history to `git log` and the Pull Request description.
3. **Self-Audit Checklist Before Committing a Spec:**
   - [ ] Does every procedural step use **active voice** (`<Actor> <verb> <object>`) and contain **$\le 20$ words**?
   - [ ] Does every descriptive sentence contain **$\le 25$ words** and express **one idea**?
   - [ ] Are all marketing adjectives (`"robust"`, `"seamless"`, `"novel"`, `"cutting-edge"`) removed?
   - [ ] Does every tensor/quantity specify its **shape**, **dtype**, **coordinate frame**, and **physical units** (`mm`, `deg`, `rad`, `N/kg`, `Hz`)?
   - [ ] Did you apply the **3-Question Split Test** (single `docs/SPEC.md` $\le 120$ lines vs. modular `docs/specs/00_overview.md` + `01_<module>.md`)?
   - [ ] Does every stage and quantitative claim link to an exact `file:line` or reproduction script?
