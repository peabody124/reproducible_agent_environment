---
name: isr-paper-writing
description: Guide, scaffold, edit, and critique scientific manuscripts in R. James Cotton's authentic pre-2026 (non-AI-written) scientific voice using the canonical Reproducible Agent Environment (RAE) MyST paper template (templates/myst-paper with dual ISR single-column preprint and IEEE two-column builds). Enforces flowing narrative paragraphs over AI bullet-slop, step-by-step pedagogical math introductions, "Best Method First -> Ablations That Mattered" organization, candid Limitations sections, Tufte serif figures, and the multi-cycle editing + Experimental Occam's Razor workflow.
---

# ISR Scientific Paper Writing, Pre-2026 Voice Alignment & RAE MyST Workflow (`isr-paper-writing`)

Use this skill whenever scaffolding, drafting, revising, critiquing, or auditing scientific manuscripts (`isr` single-column preprints and `ieeeconf` IEEE conference submissions such as ICORR) across the Intelligent Sensing & Rehabilitation (ISR) research portfolio.

---

## 1. Grounding in R. James Cotton's Authentic Pre-2026 (Non-AI-Written) Voice

> **CRITICAL ANTI-ECHO-CHAMBER RULE:**
> Never calibrate prose style, paragraph structure, or rhetorical transitions against **2026 manuscripts** (`B3D`, `PBL`, `CAMBR`, `FASCIA`, `BiomechGPT`, etc.), which were co-drafted or edited with AI agents. Aligning to AI-assisted papers creates a self-reinforcing echo chamber of bold-lead bullet lists, em-dash chains, and formulaic transitions.
> **Always anchor voice alignment strictly to R. James Cotton's pre-2026 (`2013–2025`) human-written papers.**

### 1.1 Querying the Pre-2026 Voice Corpus via Local Zotero API (`http://localhost:23119/api`)

Before drafting or editing any section, query the local Zotero HTTP API (available on the host and tunneled into every devcontainer at `http://localhost:23119/api`) and **filter strictly to `year <= 2025`**:

```bash
# Fetch R. James Cotton's pre-2026 (non-AI-written) publications from local Zotero
curl -s "http://localhost:23119/api/users/0/items?q=Cotton&limit=100" | python3 -c "
import json, sys, re
for it in json.load(sys.stdin):
    d = it.get('data', {})
    if d.get('itemType') in ('attachment', 'note'): continue
    m = re.search(r'(20\d\d)', d.get('date', ''))
    yr = int(m.group(1)) if m else 0
    if 2013 <= yr <= 2025:
        print(f\"{it['key']} ({yr}) [{d.get('publicationTitle') or d.get('proceedingsTitle') or 'Preprint'}]: {d.get('title')}\")
"

# Export BibTeX directly for citation keys
curl -s "http://localhost:23119/api/users/0/items?q=Cotton&format=bibtex"
```

#### Canonical Pre-2026 Human-Written Exemplars (`2013–2025`)
| Domain | Zotero Key (Year, Venue) | Title & Full-Text Reference Location (if in `/workspaces/Notes/Manuscripts/` or `/workspaces/Manuscripts/`) |
| :--- | :--- | :--- |
| **Probabilistic Computation & Structured Statistics (`2013–2021`)** | `23SPKLY6` (2013, *PNAS*)<br>`E22PCNTX` (2015, *PLoS Comp Biol*)<br>`J5B3JRRF` (2020, *Nature Neurosci*)<br>`VF2QWPFD` (2021, *Nature Comms*) | *Trial-to-trial, uncertainty-based adjustment of decision boundaries*<br>*Improved Estimation and Interpretation of Correlations in Neural Circuits* (sparse + low-rank covariance)<br>*A neural basis of probabilistic computation in visual cortex*<br>*Revealing nonlinear neural decoding by analyzing choices* |
| **Clinical Rehab, Outcomes & Precision Rehab (`2020–2024`)** | `SE8LVGCI` (2020, *IEEE BioRob*)<br>`EUWZZ49R` (2021, *Sci Reports*)<br>`GAMD4ML8` (2023–2024)<br>`8TGRW2I6` (2024, *Sci Reports*)<br>`RWKKTS5E` (2024, *JNER*) | *Smartphone Control for People with Tetraplegia by Decoding Wearable EMG*<br>*Portable, open-source solutions for estimating wrist position during reaching in people with stroke*<br>*A Causal Framework for Precision Rehabilitation* (`2023 - PrecisionRehab/Causal Framework for Precision Rehab.md` — tag `jner-submission-2025`)<br>*Validation of portable in-clinic video-based gait analysis for prosthesis users* (`MarkerlessMocapGaitRite`)<br>*Transforming modeling in neurorehabilitation: clinical insights for personalized rehabilitation* |
| **Markerless Mocap, Calibrated Pose & Differentiable Biomechanics (`2020–2025`)** | `84ENQZZ6` (2022)<br>`L7F5RXTR` (2022, *Digit Biomark*)<br>`6TWZYM4B` (2022/2023)<br>`5MZ5V29K` (2023)<br>`BYMFMV2C` (2023, *IEEE BHI*)<br>`35LAPNK8` (2024)<br>`N2PK29BL` (2024, *IEEE BioRob*)<br>`S3BSZYID` (2024/2025, *ICORR*)<br>`PXQCMRJA` (2025, *EMBC*) | *PosePipe: Open-Source Human Pose Estimation Pipeline for Clinical Research*<br>*Video-Based Pose Estimation for Gait Analysis in Stroke Survivors*<br>*Optimizing MPJPE promotes miscalibration in multi-hypothesis human pose lifting*<br>*Improved Trajectory Reconstruction for Markerless Pose Estimation*<br>*Optimizing Trajectories and Inverse Kinematics for Biomechanical Analysis of Markerless Motion Capture Data* (`MarkerlessMocapBiomechanics`)<br>*Platypose: Calibrated Zero-Shot Multi-Hypothesis 3D Human Motion Estimation*<br>*Advancing Monocular Video-Based Gait Analysis Using Motion Imitation with Physics-Based Simulation* (`Biomechanical Follower`)<br>*Differentiable Biomechanics Unlocks Opportunities for Markerless Motion Capture* (`DifferentiableBiomechanics`)<br>*Biomechanical Reconstruction with Confidence Intervals from Multiview Markerless Motion Capture* (`BiomechanicalConfidenceIntervals`) |

---

### 1.2 Five Stylistic Pillars of Pre-2026 James Cotton Prose (vs. AI-Written Slop)

Inspecting James's human-written manuscripts (`2013–2025`) reveals five concrete stylistic traits that distinguish his authentic voice from LLM-generated scientific prose:

1. **Cohesive Narrative Paragraphs Over "Bold-Lead Bullet Lists":**
   - **How James writes (pre-2026):** Every section of the Introduction, Methods, Results, and Discussion is written in **complete, flowing paragraphs** where each paragraph develops one unified idea. Bullet lists appear **only** at the end of the Introduction for the 3–4 headline contributions (or when defining a formal taxonomy in a review paper).
   - **AI habit to strip:** Never write Methods, Results, or Limitations as a sequence of `- **Bold Phrase:** sentence fragment` bullets or numbered pseudo-paragraphs. Convert bulleted body text back into connected narrative prose.

2. **Plainspoken, Direct Scientific Motivation ("What We Truly Need"):**
   - **How James writes (pre-2026):** Before introducing any formalism, James states the practical clinical or measurement bottleneck in plain, unpretentious English:
     - *"However, this does not provide the information truly needed -- how accurate is a particular measurement with a novel camera configuration on the next current participant?"* (`BiomechanicalConfidenceIntervals`, 2025)
     - *"These confidence intervals are much more useful than the quality metrics we previously used, such as the mean reprojection error. They directly reflect what we want - how accurately we are tracking joint angles and body segment positions at each moment of time."* (`BiomechanicalConfidenceIntervals`, 2025)
     - *"We intentionally recruited a diverse rehabilitation population both to ensure the system was robustly validated for all types of patients, and because this is the population we intend to apply this final system to."* (`MarkerlessMocapBiomechanics`, 2023)

3. **Pedagogical, Step-by-Step Mathematical Introductions (Never "Equation Dump + Symbol Glossary"):**
   - **How James writes (pre-2026):** James never drops a 6-term composite loss equation cold and follows it with a bulleted `where $\lambda_1$ is...` glossary. Instead, he walks the reader through the forward generative or physical process in prose, introducing each operator inline as it acts on the state, explains *why* the naive calculation fails, and then displays the compact equation:
     - *"The pose parameters predict the detected keypoint locations through two non-linear steps. First, the marker locations can be predicted in 3D space from the pose parameter using the forward kinematic model of the body, $\mathcal{M}_\beta: \boldsymbol{\theta} \rightarrow \mathbf{x}$... Next, these marker locations are projected into the image plane using the calibrated camera model, $\Pi_c: \mathbf{x} \rightarrow \hat{\mathbf{y}}^c$... In principle, we could compute the posterior of the pose trajectory given the observations using Bayes' rule... However, this is challenging because we do not have the normalization factor $p(\mathbf{Y}_t, \mathbf{S}_t)$... Because $p(\mathbf{Y}, \mathbf{S})$ is a constant, we can maximize the Evidence Lower Bound (ELBO) to minimize the KL divergence:"* (`BiomechanicalConfidenceIntervals`, 2025)

4. **Measured, Understated Empirical Claims (Zero Marketing Adjectives):**
   - **How James writes (pre-2026):** Quantitative improvements speak for themselves, framed with measured scientific restraint:
     - *"Our fairly low ECE scores suggest our confidence intervals are fairly well calibrated, meaning 95% of the time, the ground truth should fall within our 95% confidence intervals."*
     - *"We also found some indications that it is less inclined to fall into local minima than our prior deterministic method..."*
     - *"Fairly unsurprisingly, policies driven by keypoints from video produced greater tracking errors and errors for spatial gait parameters than policies driven by ground truth data."*
   - **Banned AI hype vocabulary:** Strip words like *"paradigm-shifting"*, *"unprecedented"*, *"seamlessly"*, *"crucially"*, *"remarkably"*, *"delves into"*, *"testament to"*, *"pivotal"*, *"synergistic"*, *"holistic"*, and *"underscores"*.

5. **Candid Operational Transparency on Negative Results, Compute Costs & Model Mismatches:**
   - **How James writes (pre-2026):** Rather than hiding what failed or writing generic AI boilerplate (`"Future work will explore larger datasets"`), James candidly reports negative experimental branches, real GPU wall-clock costs, and biomechanical model simplifications:
     - *"We also implemented short horizon actor-critic in Brax as an optimizer, given the claim it can produce more precise tracking for differentiable environments. However, we found that it was extremely slow to train and could not obtain good policies."* (`Biomechanical Follower`, 2024)
     - *"However, our method also has limitations. Optimizing the probabilistic representation is several times slower than our non-probabilistic implicit representation; for example, 10-20 trials can take 1-2 hours on an A100. Our synthetic testing also revealed that certain modeling discrepancies, such as errors in the calibration, can produce overly confident results by attributing too much uncertainty to the likelihood function."* (`BiomechanicalConfidenceIntervals`, 2025)
     - *"We focused on only sagittal plane joint angles as we anticipated the vast differences between our simplified humanoid model and the accurate biomechanical model used in the mocap data would be too significant of a model mismatch."* (`Biomechanical Follower`, 2024)

#### Quick Reference: AI-Drafted Slop vs. Authentic Pre-2026 James Cotton Voice
| Dimension | AI-Drafted Slop (Rewrite Immediately) | Authentic Pre-2026 James Cotton Prose |
| :--- | :--- | :--- |
| **Body Structure** | Wall of `- **Bold Header:** sentence` bullets in Methods, Results, and Limitations | Cohesive narrative paragraphs; bullets reserved for the 3–4 Intro contributions |
| **Punctuation** | Heavy em-dash chains (`— ... —`) and rhetorical colon headers (`Key Insight: ...`) | Clean declarative sentences, natural subordinate clauses (`although`, `while`, `because`) |
| **Math Presentation** | Giant 7-term $\mathcal{L}_{\text{total}} = \sum \lambda_i \mathcal{L}_i$ dump + symbol list | Step-by-step inline prose walkthrough of the forward model $\to$ why naive inference fails $\to$ compact objective |
| **Tone & Claims** | *"Crucially, our novel framework seamlessly achieves unprecedented accuracy..."* | *"This end-to-end approach produced lower reprojection errors than a traditional multistage pipeline..."* |
| **Limitations** | Vague boilerplate (*"Future work will expand to larger cohorts and real-time deployment"*) | Specific physical/compute candor (*"10–20 trials take 1–2 hours on an A100; calibration errors can produce overconfident posteriors by inflating the learned likelihood width"*) |

---

### 1.3 Strict Ban on Internal Code, Config, & Lab-Notebook Jargon

Never leak internal codebase identifiers, run tags, checkpoint filenames, or config flags into manuscript prose, tables, or figure labels:

| Banned Internal Jargon | Clean Scientific Terminology |
| :--- | :--- |
| `O_v48`, `O_v48_s0`, `v4.7`, `fits_v47` | **Pointwise Regression (`FASCIA-Pointwise`)**, **CT registration archive** |
| `whole_v47_c6p`, `c6b`, `flow_calib` | **Conditional Flow Matching (`FASCIA-Flow`)** |
| `humanoid_simple_arm_20261021.xml`, `correspondence_20261026` | **CT-calibrated anatomical skeleton**, **calibrated surface-to-skeleton correspondence model** |
| `"CT skeleton"` (when applied to non-CT subjects like amputees or gait patients) | **Anatomically calibrated reference skeleton** *(never imply participants had CT scans when they did not!)* |
| `dualhead_C_20261026`, `pseudoanchor_scratch_tgoff` | **Unified dual-head multi-view transformer**, **online pseudo-anchor supervision** |
| `carry3sh`, `carry3shac`, `dvltqft` | **Carried Gaussian decoder with spatial-hash query selection**, **velocity-continuity regularization** |
| `NLF v0.2.0` vs. `NLF v0.3.2` | Report **only one `NLF` baseline** (the faithful port of the original NLF paper, called simply **`NLF`**) alongside **`MAMMA`** and **`CSE`** |
| `unified_v4_31b_grpo_perc_nf_v2`, `c0 + c1 * z`, `M5 b3d` | **GRPO reinforcement learning with verifiable kinematics rewards**, **affine calibration**, **monocular mesh baseline** |

---

## 2. Canonical RAE MyST Paper Template (`templates/myst-paper/`)

Every ISR manuscript across all repositories **must** be authored in **MyST Markdown (`mystmd`)** using the canonical template in `reproducible_agent_environment/templates/myst-paper/` (also mirrored in `.agents/skills/isr-paper-writing/templates/myst-paper/`). **Never hand-roll standalone LaTeX `.tex` article files.**

### 2.1 Scaffolding a New Paper in One Command

```bash
# From any repository or devcontainer with RAE installed:
/path/to/reproducible_agent_environment/templates/myst-paper/scripts/scaffold_myst_paper.sh \
  docs/papers/<paper_slug> \
  "Full Jargon-Free Paper Title" \
  "<paper_slug>"
```

### 2.2 Canonical Directory Layout (`docs/papers/<paper_slug>/`)

```text
docs/papers/<paper_slug>/
├── myst.yml                     # Project config, Eq. %s numbering, references.bib, toc
├── manuscript.md                # Dual ISR + IEEE export frontmatter + modular {include} directives
├── abstract.md                  # Structured Background / Methods / Results / Conclusions abstract
├── introduction.md              # 4-paragraph clinical/scientific hook -> gap -> unified method -> contributions
├── methods.md                   # Best unified method first, with <!-- CODE: file:line --> anchors
├── results.md                   # Primary benchmark -> physical/clinical validation -> ablations that mattered
├── discussion.md                # Synthesis + forthcoming "Limitations and Future Directions" subsection
├── acknowledgments.md           # Funding, cohort, and mandatory AI usage acknowledgment
├── appendix.md                  # Exhaustive per-bone/per-joint tables, derivations, sensitivity grids
├── references.bib               # Populated via local Zotero API (http://localhost:23119/api)
├── BUILD.md                     # Git commit provenance table + exact reproduction commands
├── build_isr.sh                 # MyST -> XeLaTeX + Biber -> 2x XeLaTeX + unresolved-citation gate
├── build_ieee.sh                # MyST -> XeLaTeX + Biber -> 2x XeLaTeX (ieeeconf) + unresolved-citation gate
├── scripts/
│   ├── generate_paper_figures.py # Deterministic Tufte serif figure generator
│   └── diff_commits_pdf.py       # Word-level redline PDF diff between any 2 Git commits/tags/WORKTREE
└── templates/
    ├── isr/                     # isrpaper.cls, isr-logo.pdf, template.tex, template.yml (single/two-col, orange/blue)
    └── ieeeconf/                # ieeeconf.cls, template.tex, template.yml
```

### 2.3 Key Build & Provenance Rules in the RAE MyST Template

1. **Modular `{include}` Architecture (`manuscript.md`):**
   - Keep `manuscript.md` as a thin frontmatter + `{include}` spine (`abstract.md`, `introduction.md`, `methods.md`, `results.md`, `discussion.md`, `acknowledgments.md`, `appendix.md`). If a conference submission requires a separate supplementary PDF (`manuscript_conf.md` + `supplementary.md`), both include the exact same section `.md` files so numbers and text can never drift between ISR and conference builds.
2. **Preventing MyST `.bib` Culling (`cp references.bib main.bib`):**
   - `myst build --tex` writes a culled `main.bib`. Both `build_isr.sh` and `build_ieee.sh` automatically overwrite `main.bib` with `references.bib` and copy `templates/isr/{isrpaper.cls,isr-logo.pdf}` into the working directory before running `xelatex` + `biber` + `xelatex` $\times 2$, then grep the `.log` to hard-fail on any undefined citation (`?`).
3. **Code-to-Paper Provenance Anchors (`<!-- CODE: path:Lstart-Lend -->`) & `BUILD.md`:**
   - Every architectural claim, loss term, and evaluation metric in `methods.md` and `results.md` should carry an HTML comment anchoring it to the exact source file and line range (`<!-- CODE: src/pkg/model.py:L120-L155 -->`), and `BUILD.md` must record the git commit SHA and exact CLI invocations that produced every table and figure.
4. **Mandatory AI Usage Acknowledgment (`acknowledgments.md`):**
   - Every ISR manuscript must include `acknowledgments.md` in `manuscript.md` with the standard AI-assistance disclosure (included by default in `templates/myst-paper/acknowledgments.md`):
     > *"AI-assisted coding and research agents, including Claude (Anthropic) and Google Antigravity, were used for code development, running experiments, and assistance with manuscript preparation. The manuscript was extensively reviewed and verified by the authors, who take full responsibility for its content."*

---

## 3. Organizational Strategy: "Best Method First $\to$ Ablations That Mattered"

Never organize a paper as a chronological lab notebook (`"First we tried X, then we fixed bug Y, then in v3 we tried Z..."`). Structure every manuscript around **the strongest unified method first**, followed by **targeted ablations and lesions** that isolate why each component is necessary:

1. **Introduction (`1–1.25` pages, 4–5 narrative paragraphs):**
   - **Paragraph 1 (Clinical / Scientific Need):** What measurement or control capability does rehabilitation or movement science need, and why is it inaccessible at scale?
   - **Paragraph 2 (Why Existing Silos Fall Short):** Contrast traditional laboratory optical mocap / CT imaging (accurate but restricted) against commodity computer vision pose/mesh estimators (scalable but biomechanically uncalibrated, lacking joint-axis fidelity, calibrated uncertainty, or physical consistency).
   - **Paragraph 3 (Core Insight & Unified Method):** Walk through how our unified formulation bridges this gap in plain, concrete terms.
   - **Paragraph 4 (Contributions & Validation Summary):** `3–4` crisp bullets summarizing the method, the validation cohort, and the headline findings.
2. **Methods (Lead with the Best Unified Architecture):**
   - Present the **complete, best-performing formulation** as a cohesive pipeline from inputs to outputs in flowing narrative paragraphs.
   - Relegate historical precursors, alternative parameterizations, or secondary variants to the **Ablation Study** subsection of Results or the **Appendix**.
3. **Results (Primary Benchmark $\to$ Physical/Clinical Validation $\to$ Ablations & Lesions):**
   - **3.1 Primary Head-to-Head Comparison:** Compare our unified method against established external baselines.
   - **3.2 Physical, Anatomical, or Clinical Validation:** Validate against independent gold-standard measurements (CT holdout scans, dual AMTI forceplates, C3D optical markers, whole-body DEXA, GaitRite, or clinical scales).
   - **3.3 Ablation & Lesion Studies ("What Mattered?"):** Systematically remove or swap key components (or compare against simpler formulations tested during our simplification cycle) so the reader sees empirically *why* each component earns its keep.
4. **Discussion & Candid Limitations (`Limitations and Future Directions`):**
   - Include a dedicated, concrete subsection candidly exposing: (a) **physical observability limits** (what cannot be inferred from the modality alone), (b) **training data / field-of-view coverage gaps** (e.g., truncated distal forearms in clinical trunk CTs, adult body priors on infants), (c) **biomechanical/sensor simplifications & compute costs** (e.g., rigid prosthetic foot segments, optimization wall-clock time), and (d) **how each limitation directly motivates the next step**.

---

## 4. Multi-Cycle Paper Development & Improvement Workflow (Cycles 0–5)

We develop and polish papers through an iterative, six-stage loop that tightly couples **pre-2026 voice alignment**, **code-to-paper verification**, and **experimental simplification**:

```
Cycle 0 (RAE MyST Scaffold & BUILD.md Provenance)
  │
  ▼
Cycle 1 (Pre-2026 Zotero Voice & Literature Grounding — year <= 2025 only)
  │
  ▼
Cycle 2 (Round-1 Three-Subagent Review Triad: Code/Jargon + Pre-2026 Voice + Peer-Reviewer/Simplification)
  │
  ▼
Cycle 3 (Experimental Occam's Razor Loop: Methods Smell-Test -> Fast GPU Simplification Ablation)
  │
  ▼
Cycle 4 (Round-2 Deep Audit: Code/Eval Bugs Exposed by Writing, Participant-Level DoF & Label-Blindness)
  │
  ▼
Cycle 5 (Tufte Serif Figures, Dual ISR/IEEE PDF Build, Visual Page Inspection & Redline Diff PDF)
```

### Cycle 0 — Scaffold from RAE `templates/myst-paper` & Stamp Provenance
- Initialize `docs/papers/<paper_slug>/` using `templates/myst-paper/scripts/scaffold_myst_paper.sh`.
- Record the baseline git commit SHA, branch, and evaluation script commands in `BUILD.md`.

### Cycle 1 — Pre-2026 Voice Calibration & Literature Grounding via Local Zotero (`127.0.0.1:23119`)
- Query `http://localhost:23119/api/users/0/items?q=Cotton&limit=100` filtered to **`year <= 2025`** and read 1–2 closest pre-2026 human-written manuscripts by R. James Cotton (e.g., `BiomechanicalConfidenceIntervals.md`, `Differentiable Biomechanics.md`, `Biomechanical Follower.md`, `Causal Framework for Precision Rehab.md`) before drafting or rewriting prose.
- Populate `references.bib` directly from Zotero (`?format=bibtex`) so every citation key is verified against real metadata (no hallucinated BibTeX entries).

### Cycle 2 — Round-1 Three-Subagent Review Triad
Spawn three parallel subagents with non-overlapping responsibilities:
1. **Subagent 1 — Code-to-Paper, Statistical-Unit & Jargon Auditor:**
   - Verifies every equation, symbol, sample size $N$, and table number against the exact production Python scripts (`<!-- CODE: file:line -->`) and JSON evaluation outputs.
   - Strips all internal run tags (`O_v48`, `fits_v47`, `carry3sh`, `"CT skeleton"` on non-CT cohorts) and checks that external baselines are faithfully represented.
   - **Code-Complexity Smell Test:** Flags any Methods passage where describing the code requires listing multi-stage heuristics, magic thresholds, or unablated sub-modules.
2. **Subagent 2 — Pre-2026 James Cotton Voice, Narrative Flow & Candid Limitations Editor:**
   - Explicitly compares the draft against James's **pre-2026 (`<= 2025`) human-written papers** (never 2026 AI drafts).
   - Converts `- **Bold Header:**` bullet-list slop in Methods, Results, and Discussion back into cohesive narrative paragraphs.
   - Rewrites cold equation dumps into step-by-step inline prose introductions, strips AI hype adjectives, enforces **"Best Method First $\to$ Ablations That Mattered"**, moves secondary tables to `appendix.md`, and ensures the **Limitations** section is candid and specific.
3. **Subagent 3 — Adversarial Peer-Reviewer, Simplification Experiment Designer & Figure-to-Point Critic:**
   - Visually inspects every figure and rendered PDF page via `read_file` to verify that each figure proves one unmistakable scientific claim with zero text overlaps or aspect-ratio distortions.
   - **Simplification Mandate:** For every complex component or multi-stage rule in Methods, asks: *"Have we tested whether a simpler, single-objective formulation works just as well or better?"* and designs a fast GPU ablation (`15-Minute Rule`).

### Cycle 3 — The Experimental Occam's Razor Loop ("Don't Guess—Test It")
1. **Methods-Drafting as an Architectural Smell Test:**
   - When a Methods paragraph feels clunky or apologetic (`"First we apply heuristic A with threshold $\tau_1$, then for stationary tracks we switch to heuristic B..."`), treat it as an **architectural smell in the code**, not merely a writing problem.
2. **Run the Fast GPU Simplification vs. Complexity Experiment:**
   - We are not dogmatically anti-complexity—we are against *untested, unearned complexity*.
   - Implement the cleaner single-objective formulation alongside the complex one and run a targeted head-to-head GPU evaluation.
3. **Promote on Win/Tie, or Document as an "Ablation That Mattered":**
   - **If the simpler formulation matches or beats the complex one:** Promote the simpler code to production, delete the dead heuristics, and present the clean formulation as our primary Method.
   - **If the richer formulation wins significantly:** Keep it in the primary Method and report the simpler baseline in the **Ablation Study ("What Mattered?")** subsection of Results so every piece of complexity is empirically justified.

### Cycle 4 — Round-2 Deep Verification Audit (Bugs Exposed by Writing)
Writing the paper alongside the code routinely exposes subtle evaluation or modeling bugs. Before finalizing any manuscript, run a dedicated Round-2 verification pass checking:
1. **Statistical Unit of Analysis & Degrees of Freedom:** Never treat repeated trials, strides, or frames from the same participant as independent samples in $t$-tests or $p$-values (e.g., 59 trials across $N=12$ participants must use participant-level paired statistics or mixed-effects models with $df = N - 1$, never trial-level $df = 58$).
2. **Strict Label-Blindness at Inference:** Verify in code that no evaluation metric or test-time inference path leaks ground-truth clinical labels, ground-truth body mass/height (when evaluating video-only prediction), or post-hoc per-trial bias subtraction without calling it out explicitly.
3. **Metric & Baseline Parity:** Verify that baselines and our model are evaluated on the exact same frames, coordinate conventions (`KAD1-IMR` vs. `CMR`), and unit scales (`mm` vs. `cm`).

### Cycle 5 — Tufte Serif Figures, Dual PDF Compilation, Visual Inspection & Redline Diff PDF
1. **Tufte Serif Figure Generation (`scripts/generate_paper_figures.py`):**
   - Use serif typography (`DejaVu Serif` / `Times`, `mathtext.fontset = "stix"`) with mathematical symbols identical to `methods.md`.
   - Use left-aligned 2-line panel headers (**bold** panel letter + claim on line 1; muted `#475569` subtitle with $N$, units, and statistic on line 2), despined top/right axes, and `1:1` native pixel aspect ratios (`aspect="equal"`) on all camera crops and 3D renders.
2. **Dual ISR & IEEE Compilation + Page-by-Page Visual Inspection:**
   - Run `./build_isr.sh` and `./build_ieee.sh`, render pages to PNG (`pdftoppm -png -r 150 <paper>_isr.pdf page`), and visually inspect every page (or preview live in **Sheprd MyST Studio** via `./sheprd myst` on `http://127.0.0.1:7319`).
3. **Word-Level Redline Diff PDF (`scripts/diff_commits_pdf.py`):**
   - Whenever completing an editing cycle or preparing a revision for co-author review, generate a publication-style inline word-diff PDF comparing the baseline commit/tag against the updated manuscript:
     ```bash
     python scripts/diff_commits_pdf.py <baseline_commit_or_tag> WORKTREE -f manuscript.md -o exports/manuscript_diff.pdf
     ```
