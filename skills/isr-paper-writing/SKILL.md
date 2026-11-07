---
name: isr-paper-writing
description: Guide, scaffold, edit, and critique scientific manuscripts in R. James Cotton's authentic pre-2026 (non-AI-written) scientific voice using the canonical Reproducible Agent Environment (RAE) MyST paper template (templates/myst-paper with dual ISR single-column preprint and IEEE two-column builds). Enforces flowing narrative paragraphs over AI bullet-slop, step-by-step pedagogical math introductions, "Best Method First -> Ablations That Mattered" organization, candid Limitations sections, Tufte serif figures, and the multi-cycle editing + Experimental Occam's Razor workflow.
---

# ISR Scientific Paper Writing, Pre-2026 Voice Alignment & RAE MyST Workflow (`isr-paper-writing`)

Use this skill whenever scaffolding, drafting, revising, critiquing, or auditing scientific manuscripts (`isr` single-column preprints and `ieeetrans` / conference submissions) across the Intelligent Sensing & Rehabilitation (ISR) research portfolio.

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

3. **Pedagogical 3-Part Loss & Equation Introductions (Brief Intuition $\to$ Equation $\to$ Term Details):**
   - **How James writes:** Whenever introducing a loss function or optimization objective, follow a crisp 3-part rhythm:
     1. **Brief intuitive explanation (1–2 sentences):** State directly what the objective/loss achieves at a high level before displaying math (avoiding multi-paragraph storytelling preambles).
     2. **Displayed equation:** Present the clean equation, using `\underbrace{...}_{\text{...}}` annotations where helpful so the reader can see the role of each term at a glance.
     3. **Details of the equation:** Immediately after the equation, concisely explain the symbols and what each term does (moving low-level numerical/implementation minutiae to the Appendix).
   - **Example from pre-2026 prose:**
     - *"The pose parameters predict the detected keypoint locations through two non-linear steps. First, the marker locations can be predicted in 3D space from the pose parameter using the forward kinematic model of the body, $\mathcal{M}_\beta: \boldsymbol{\theta} \rightarrow \mathbf{x}$... Next, these marker locations are projected into the image plane using the calibrated camera model, $\Pi_c: \mathbf{x} \rightarrow \hat{\mathbf{y}}^c$... Because $p(\mathbf{Y}, \mathbf{S})$ is a constant, we can maximize the Evidence Lower Bound (ELBO) to minimize the KL divergence:"* (`BiomechanicalConfidenceIntervals`, 2025)

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
├── build_ieee.sh                # MyST -> pdflatex + Biber -> 2x pdflatex + unresolved-citation gate
├── scripts/
│   ├── generate_paper_figures.py # Deterministic Tufte serif figure generator
│   └── diff_commits_pdf.py       # Word-level redline PDF diff between any 2 Git commits/tags/WORKTREE
└── templates/
    ├── isr/                     # isrpaper.cls, isr-logo.pdf, template.tex, template.yml (single/two-col, orange/blue)
    └── ieeetrans/               # IEEEtran.cls, template.tex, template.yml
```

### 2.3 Key Build & Provenance Rules in the RAE MyST Template

1. **Modular `{include}` Architecture (`manuscript.md`):**
   - Keep `manuscript.md` as a thin frontmatter + `{include}` spine (`abstract.md`, `introduction.md`, `methods.md`, `results.md`, `discussion.md`, `acknowledgments.md`, `appendix.md`). If a conference submission requires a separate supplementary PDF (`manuscript_conf.md` + `supplementary.md`), both include the exact same section `.md` files so numbers and text can never drift between ISR and conference builds.
2. **Preventing MyST `.bib` Culling (`cp references.bib main.bib`):**
   - `myst build --tex` writes a culled `main.bib`. Both `build_isr.sh` and `build_ieee.sh` automatically overwrite `main.bib` with `references.bib` and copy `templates/isr/{isrpaper.cls,isr-logo.pdf}` into the working directory before running `xelatex` + `biber` + `xelatex` $\times 2$, then grep the `.log` to hard-fail on any undefined citation (`?`).
3. **Code-to-Paper Provenance Anchors (`<!-- CODE: path:Lstart-Lend -->`) & `BUILD.md`:**
   - Every architectural claim, loss term, and evaluation metric in `methods.md` and `results.md` should carry an HTML comment anchoring it to the exact source file and line range (`<!-- CODE: src/pkg/model.py:L120-L155 -->`), and `BUILD.md` must record the git commit SHA and exact CLI invocations that produced every table and figure.

---

## 3. Organizational Strategy: "Best Method First $\to$ Ablations That Mattered"

Never organize a paper as a chronological lab notebook (`"First we tried X, then we fixed bug Y, then in v3 we tried Z..."`). Structure every manuscript around **the strongest unified method first**, followed by **targeted ablations and lesions** that isolate why each component is necessary:

1. **Introduction (`1–1.25` pages, 4–5 narrative paragraphs):**
   - **Paragraph 1 (Clinical / Scientific Need):** What measurement or control capability does rehabilitation or movement science need, and why is it inaccessible at scale?
   - **Paragraph 2 (Why Existing Silos Fall Short):** Contrast traditional laboratory optical mocap / CT imaging (accurate but restricted) against commodity computer vision pose/mesh estimators (scalable but biomechanically uncalibrated, lacking joint-axis fidelity, calibrated uncertainty, or physical consistency).
   - **Paragraph 3 (Core Insight & Unified Method):** Walk through how our unified formulation bridges this gap in plain, concrete terms.
   - **Paragraph 4 (Contributions & Validation Summary):** `3–4` crisp bullets summarizing the method, the validation cohort, and the headline findings.
   - **Strict Introduction Hygiene Rules (No Unintroduced Acronyms/Math & No Results Data Dumps):**
     - **Spell Out Every Acronym on First Use:** Never use an acronym (e.g., `LOSO` for leave-one-subject-out, `SynX`, `FSM`, `CMT`) before defining it in full on first occurrence in the text.
     - **Zero Unintroduced Mathematical Notation in the Introduction:** Never drop un-introduced parameter symbols or subscripted math ($\uparrow\kappa_{\text{SOL,GAS}}^V$, $\downarrow\alpha_{\text{SOL,GAS}}^{\text{strength}}$, $\theta_{\text{reflex}}$) into the Introduction. Explain physiological and algorithmic mechanisms intuitively in plain prose in the Introduction, and introduce formal parameter vectors ($\theta \in \mathbb{R}^P$) sequentially in the Methods where the circuit/model is defined.
     - **No Quantitative "Data Dumps" in the Introduction:** You may preview the study design and state the high-level conclusions in the Introduction, but never dump laundry lists of correlation coefficients ($r=0.682\text{--}0.804$), $p$-values, or unmotivated muscle-specific breakdowns (e.g., naming individual deep muscles before the reader knows why they matter). Save detailed quantitative numbers for the Results section.
     - **No Overly Busy Diagrams as Figure 1:** Keep Figure 1 focused and immediately legible as a high-level paper overview; move dense multi-module wiring/block diagrams to the Supplementary or graphical abstract.
2. **Methods (Lead with What We Actually Did — Never Belabor What We Didn't Do):**
   - Present the **complete, best-performing formulation** as a cohesive pipeline from inputs to outputs in flowing narrative paragraphs.
   - **Make the Loss, Targets, & Stage Rationale Unmistakable to a Naive Reader:** Always state explicitly what the parameter vector $\theta \in \mathbb{R}^P$ controls *before* differentiating with respect to it, what exact loss function is being minimized, and what measured signals are being fit. Whenever a multi-stage procedure is used (e.g., teacher-to-student distillation), state up front *why* the first stage cannot be deployed directly at test time (or, if it can, apply Occam's Razor and remove the extra stage). When synthetic validation data is used, explain in Methods how synthetic controllers/trials are parameterized so the validation is falsifiable and non-circular.
   - **Do Not Belabor Pruned Pathways or Replaced Precursors in Main Methods:** Never spend main-text Methods paragraphs or equations explaining pathways we pruned (e.g., collinear static spindle length feedback $\kappa_i^L$), legacy four-sphere contact models we replaced, or speculative mono- vs. bi-articular arguments we did not experimentally test. Focus the main Methods 100% on what we actually did; mention pruned components in 1–2 sentences of prose in the Discussion and relegate collinearity/Fisher pruning math to `appendix.md`.
   - **Distinguish Native Simulator Physics vs. Custom Intercessions:** Clearly state what is provided natively by the physics engine (e.g., standard MJX contact/COP readout used strictly as a validation signal) versus where we interceded with custom biomechanics (e.g., a custom muscle or reflex model, which should be backed by an ablation).
3. **Results (Standard `# Results` Heading: Primary Benchmark $\to$ Physical/Clinical Validation $\to$ Ablations & Lesions):**
   - Always use the standard filename `results.md` and top-level heading `# Results` (not `# Experiments and Results` or `results_and_lean.md`) so MyST Studio parses section keys cleanly.
   - **3.1 Primary Head-to-Head Comparison:** Compare our unified method against established external baselines.
   - **3.2 Physical, Anatomical, or Clinical Validation:** Validate against independent gold-standard measurements (CT holdout scans, dual AMTI forceplates, C3D optical markers, whole-body DEXA, GaitRite, or clinical scales).
   - **3.3 Ablation & Lesion Studies ("What Mattered?"):** Systematically remove or swap key components (or compare against simpler formulations tested during our simplification cycle) so the reader sees empirically *why* each component earns its keep.
4. **Discussion & Candid Limitations (`Limitations and Future Directions`):**
   - Include a dedicated, concrete subsection candidly exposing: (a) **physical observability limits** (what cannot be inferred from the modality alone), (b) **training data / field-of-view coverage gaps** (e.g., truncated distal forearms in clinical trunk CTs, adult body priors on infants), (c) **biomechanical/sensor simplifications & compute costs** (e.g., rigid prosthetic foot segments, optimization wall-clock time), and (d) **how each limitation directly motivates the next step**.

### 3.1 Direct, Punchy, Point-Driven Prose & The "3–4 Main Points Spine" (Zero Throat-Clearing)

AI drafts often eliminate bullet lists only to replace them with winding, 45-word multi-clause paragraphs that bury the point in passive throat-clearing. R. James Cotton's authentic pre-2026 (`<= 2025`) prose is **direct, punchy, and tightly organized around a small number of explicit points**:

1. **Define the 3–4 Main Points Before Writing (`methods_outline.md`):**
   - Every paper must state its **3–4 core points (punchlines)** at the top of `methods_outline.md`, paired with: (a) the exact dataset, subject/trial count ($N$ participants / $n$ trials), and fraction of the full cohort vs. pilot data used, (b) the primary metric/effect size supporting the point, and (c) the specific figure that visually proves it.
   - Frame engineering papers around an **empirical discovery arc**: *"Before starting this study, we did not know how to do $X$ optimally (or whether $A$ was necessary over $B$); through targeted experiments and ablations, we now know $Y$."*
2. **One Point Per Paragraph (Topic Claim $\to$ Mechanism/Evidence $\to$ Punchy Takeaway):**
   - **Sentence 1 (Direct Point, $<22$ words):** Open every paragraph with a direct, active-voice claim or question. Cut all throat-clearing (*"In order to address the aforementioned challenges associated with..."*, *"It is important to note that within the context of..."*).
     - *Bad (Diffuse):* *"In order to mitigate the sensitivity of monocular 3D human mesh recovery to partial clinician-hand occlusions during clinical spasticity assessments, we incorporate an uncertainty-aware canonical landmark weighting scheme."*
     - *Good (Direct & Punchy):* *"Clinician hands frequently occlude the patient's forearm during passive stretch exams. Weighting each canonical landmark by its predicted Laplace uncertainty prevents occluded vertices from corrupting the elbow angle trajectory."*
   - **Middle Sentences:** Walk through the math or empirical numbers step by step without stacked participial tails (*"..., leveraging X, thereby enabling Y, while simultaneously mitigating Z"*).
   - **Final Sentence:** State the concrete takeaway or transition cleanly to the next step.
3. **Ban Unnatural Framework Buzzwords, Inline Number Dumps in Prose, & Walls of Tables (`ICK!`):**
   - Never invent pompous structural labels like *"Three-Pillar Architecture"*, *"Dual-Paradigm Synergistic Framework"*, or *"Four-Tiered Holistic Pipeline"*. Describe what the code does in plain biomechanics and optimization language.
   - **Put Numbers in Programmatically Generated Tables (and Figures), Not Inline Prose Dumps:** There should **not** be tons of numbers in running text—most quantitative results belong in compact, **programmatically generated tables** (generated by committed scripts in `docs/papers/<paper_slug>/scripts/` from committed evaluation JSONs) or data-driven figures. Running prose should focus on the scientific insight, physical mechanism, and what the comparison proves (referencing `{numref}\`tab-xyz\`` / `{numref}\`fig-xyz\``, with at most a single headline anchor number where helpful), rather than stringing parenthetical metric dumps (`(RMSE = X ± Y, r = Z, p = W vs. A ± B)`) through every sentence. This guarantees that numbers are programmatically generated and stay 100% synchronized while producing much cleaner, more readable prose.
   - **Distinguish True Scientific Ablations From Trivial Bug Fixes / Early Suboptimal Choices:** Not every iteration needs to be an ablation table or figure. Reserve formal ablations strictly for core architectural components where high-quality quantitative metrics are needed to prove why our final algorithm requires that component. Early engineering lessons or suboptimal parameterizations with hindsight (e.g., that an early oversized `bofoot.stl` foot mesh was bad) belong as **at most a single concise sentence in the Discussion**, never a dedicated ablation table.
   - **100% Locked-Down `methods_outline.md` & Zero `scratch/` Code Dependencies:** Every paper must maintain a 100% locked-down `methods_outline.md` (with exact `file:line` pointers, formulas, hyperparameters, and inputs/outputs matching the manuscript and production code). All code discussed in the manuscript must be migrated out of `scratch/` into committed production modules (`src/`) or into `docs/papers/<paper_slug>/scripts/` (if it only drives paper-specific evaluations, tables, or figures) and committed to git.
   - **No Walls of Tables:** Main-text tables must be compact ($\le 6\text{–}8$ rows, $\le 5\text{–}6$ columns) and answer one focused question. If a table exceeds 8 rows or 6 columns, convert the core comparison into a Tufte figure (slope graph, forest plot, or complexity ladder) and move the exhaustive breakdown to `appendix.md`.
4. **Canonical Fleet Terminology & Intellectual Lineage:**
   - Use **`CSE` (`CanonicalSapiensEqx`)** strictly for the vision backbone that predicts dense canonical surface queries and uncertainties, and **`CAMBR`** strictly for the bilevel monocular and multi-view biomechanical reconstruction method that optimizes `MHR` meshes and `BodyModels` skeletons from canonical queries.
   - Ground `CAMBR` in the intellectual lineage of our prior differentiable biomechanics (`MuJoCo`/bilevel IK) and `PBL` (Probabilistic Body Localization) papers: keypoints are robust to appearance shifts, and optimizing a biomechanical skeleton through a bilevel framework yields substantially higher anatomical accuracy than feed-forward mesh regression (`B3D`) alone.

### 3.2 Point-Driven Visual Cadence: Overview (TikZ) $\to$ Qualitative Biomechanical Overlays $\to$ Tufte Quantitative & Occam's Razor Figures (Flexible, Non-Rigid)

Every figure in a manuscript must exist to prove one of the paper's main points to a reader who skims all figures before reading the text. Often in our papers it makes sense to follow a **3-tier visual cadence**—while keeping this pattern **explicitly non-rigid** whenever a paper's specific claims align better a different way:

1. **Tier 1 — Method / Architecture Overview Figure (Often Standalone TikZ / Vector Schematic + Optional Mini-Renders):**
   - Show the conceptual and mathematical pipeline at a glance (`Inputs -> Canonical Queries / Latent Representations -> Physics / Optimization -> Outputs`), explicitly contrasting the **Primary Best Pathway** against any **Ablation Pathway** with inline loss symbols ($\mathcal{L}_{\text{NLL}}$, $\mathcal{L}_{\text{prior}}$).
   - **Exemplars:** `fig1_cambr_architecture_pathways.png` (2-pane CAMBR vector schematic contrasting Pathway A vs. Ablation Pathway B), `fig_fascia_flow_architecture_and_samples.png` (Panel a Eulerian–Lagrangian flow diagram paired with anatomical samples), and `bga_fig1_architecture_overview.png`.
   - **Hard Rule:** Build pipeline overviews in TikZ/vector PDF or tightly audited SVG—never ship boxy matplotlib rectangle diagrams with clipped text or arrow collisions (avoid right-edge text clipping).
2. **Tier 2 — Qualitative Biomechanical Overlay & Physical Convincer Figure:**
   - Immediately show that the method works visibly on real movement data across views, occlusions, or clinical conditions.
   - **Mandatory Visual & Geometric Standards:**
     - **Camera Distortion Correction (`multi_camera` JAX):** Project 3D meshes, skeletons, and wheels using full OpenCV radial/tangential camera distortion coefficients ($[k_1, k_2, p_1, p_2, k_3]$ and exact principal point $(c_x, c_y)$) via `multi_camera`'s high-performance JAX camera model—and/or undistort the video images first—so overlays align pixel-accurately out to image edges.
     - **Standard GPU Cycles Mesh-Over-Skeleton Recipe:** Render the native forward-kinematics `MHR` skin as a semi-transparent pearl envelope (`alpha = 0.28–0.32`, `roughness = 0.45`), internal `.stl` bones with **Bilateral Bone Hue Coding** (`Left = Steel-Blue #7FA8D4`, `Right = Coral-Red #D98880`, `Axial/Midline = Warm Ivory #E8E2D5`), and CT-calibrated skull offset (`skull_offset_from_mhr` + `gmat`). Never use frame-0 posed-space `cKDTree` proximity skinning.
     - **Three-Gate PHI & Publication-Image Policy (`sheprd-publication-consent` skill):** (1) Verify REDCap publication-image consent (`recording == "agree"`) via Sheprd $\to$ `PosePipeAgent / 1 (eqx wK:p1)` (`redcap_consent` skill, cached in `<repo>/data_cache/publication_image_consent.json`, or use public-consent `ASB` participants; never include `disagree` / `not_answered` clinical participants); (2) blur all visible faces even for consented participants (`MHR` 3D cranial projection); and (3) **never commit participant images outside the specific publication figures directory (`docs/papers/<slug>/figures/` or `docs/manuscript/figures/`)**.
     - **Time-Locked Waveforms & Insets:** Pair image overlays with 3D studio views, high-magnification anatomical insets (e.g., $2.6\times$ hand/finger or ribcage zoom), and synchronized kinematic/GRF/EMG/reflex waveforms that never crop at panel boundaries.
   - **Exemplars:** `tremor_multiview_finger_overlay_keyframes.png`, `hop_test_triple_hop_skeleton_image_overlay_keyframes.png`, `fig_two_person_cse_mamma_contact.png`, and `fig_fascia_flow_architecture_and_samples.png` (Panels b–d).
3. **Tier 3 — High-Density Tufte Quantitative Result & Occam's Razor Ablation Figures:**
   - Present quantitative validation and complexity ablations with transparent background (`transparent=True`), serif typography (`Palatino` / `GT Sectra Fine` / `TeX Gyre Pagella` + `stix` math, `pdf.fonttype = 42`), despined axes, direct on-canvas labels, subject-level paired trajectories (`N` patients vs. trials to prevent pseudoreplication), and an explicit **Occam's Razor Complexity Ladder** whenever a simplification/ablation was tested.
   - **Exemplars:** `fig_ssrp_occams_razor_ablation.png` (M1–M5 complexity ladder showing CV $r$, BIC minimum, and paired $d_z$), `fig_real_stroke_vs_nonstroke_ssrp.png` (6-panel paired clinical validation), and `fig1_clinical_gaitlab_emg_grf.png` (8-panel EMG/GRF/CoP validation).
4. **Multi-Contrast Color Scheme Templates Across Manuscript PDF (`tufte-print`), Companion Interactive 3D Viewers (`dark-studio`), and Conference-Room TV / Slides (`bright-room-tv` & `sralab-blue-deck` in [`pasture/config/viz_color_themes.json`](file:///Users/jcotton/projects/herdr-herding/pasture/config/viz_color_themes.json)):**
   - Use **`tufte-print`** (`transparent=True`, `#111111` primary ink, `#333333` secondary ink, Left = `#1655a1`, Right = `#c0392b`, Measured = `#0b8e93`) for manuscript `.svg`/`.pdf`/`.png` figures.
   - Whenever generating companion interactive 3D HTML visualizers (`slot1_*.html` modeled on `gaitlab/slot1_gaitlab_m5_flagship_viewer.html` and `hop_test/slot1_hop_test_m5_viewer.html`) or Deckwerk presentations, wire the 1-click theme switcher (`🌙 Dark` | `☀️ TV Bright` | `🏛️ SRALab Blue`) using [`pasture/config/viz_color_themes.json`](file:///Users/jcotton/projects/herdr-herding/pasture/config/viz_color_themes.json) and the **June 2026 Shirley Ryan AbilityLab Brand Guidelines** (`PMS 2145 Deep Blue #1655a1`, `PMS 185 Red #ed1c2c`, `PMS 1505 Orange #f36c21`, `Custom Dark Teal #0b8e93`, `PMS Warm Gray 11 #6e6259`). In `bright-room-tv` mode, strictly ban low-contrast `#64748b`/`#94a3b8` grays, use `3.0 px` plot strokes, and switch the 3D scene floor to warm alabaster (`#f8fafc -> #dbe4ee`) to eliminate conference-room TV mirror glare.
5. **Non-Rigidity Guardrail:**
   - Never force a figure that does not serve the paper's core points. If a paper's 3–4 main points do not align with a TikZ overview + qualitative overlay sequence, adapt the figure architecture directly to the points being communicated.

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

### Cycle 1 — Pre-2026 Voice Calibration & Mandatory Zotero Library Grounding (`127.0.0.1:23119`)
- Query `http://localhost:23119/api/users/0/items?q=Cotton&limit=100` filtered to **`year <= 2025`** and read 1–2 closest pre-2026 human-written manuscripts by R. James Cotton (e.g., `BiomechanicalConfidenceIntervals.md`, `Differentiable Biomechanics.md`, `Biomechanical Follower.md`, `Causal Framework for Precision Rehab.md`) before drafting or rewriting prose.
- **Mandatory Zotero Library Grounding & Unambiguous Zotero Item Key (`zotero_key`):**
  - Every reference cited in our manuscripts **must be grounded in the user's Zotero library** (`http://localhost:23119/api/users/0/items`).
  - Populate `references.bib` directly from Zotero (`http://localhost:23119/api/users/0/items/<ITEM_KEY>?format=bibtex`) and include the unambiguous 8-character Zotero item identifier on every `.bib` entry (`zotero_key = {<ITEM_KEY>}`) so every reference can be deterministically audited against Zotero (`curl -s "http://localhost:23119/api/users/0/items/<ITEM_KEY>"`).
  - If a relevant external paper is **not yet in Zotero**, you must: (1) verify that the paper is 100% real via Crossref / PubMed / Semantic Scholar / arXiv (confirming exact DOI/PMID/arXiv ID, authors, title, venue, and year—never guess or synthesize BibTeX fields), (2) tag the entry with `zotero_status = {pending_user_import}` + verified `doi = {...}`, and (3) explicitly report the verified reference + DOI/URL to the user so they can add it to Zotero.

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

### Cycle 4 — Round-2 Deep Verification & Anti-Lab-Notebook Clutter Purge (Bugs & Administrative Clutter Exposed by Writing)
Writing the paper alongside the code routinely exposes both subtle evaluation bugs and "lab-notebook administrative clutter" that would never appear in a peer-reviewed journal article. Before finalizing any manuscript (or its supplement), run a dedicated Round-2 verification pass checking:
1. **Statistical Unit of Analysis & Degrees of Freedom:** Never treat repeated trials, strides, or frames from the same participant as independent samples in $t$-tests or $p$-values (e.g., 59 trials across $N=12$ participants must use participant-level paired statistics or mixed-effects models with $df = N - 1$, never trial-level $df = 58$).
2. **Strict Label-Blindness at Inference:** Verify in code that no evaluation metric or test-time inference path leaks ground-truth clinical labels, ground-truth body mass/height (when evaluating video-only prediction), or post-hoc per-trial bias subtraction without calling it out explicitly.
3. **Metric & Baseline Parity:** Verify that baselines and our model are evaluated on the exact same frames, coordinate conventions (`KAD1-IMR` vs. `CMR`), and unit scales (`mm` vs. `cm`).
4. **Gate 5 — Mandatory Anti-Lab-Notebook & Irrelevant Administrative Detail Purge (Main Text AND Supplement):**
   - **Zero Raw Calendar Visit Dates (`YYYY-MM-DD`) or Session Logs:** Never include tables or prose listing raw calendar visit dates (e.g., `2024-07-03, *2024-07-17*`, `TF70 2025-03-20... held only clinical tests`) in either the main text or the supplement. Report clinical protocol intervals in elapsed days/weeks/months (e.g., `"following a 6-week home acclimation period"`) and aggregate cohort flow counts ($N$ participants, $n$ visits, $n$ walking trials).
   - **Zero Internal Recording IDs, Filenames, Commit Hashes, or Checkpoint Codenames:** Strip raw trial recording hashes (`20240915_112405_cam01`, `ps9n02cm`, `ASB_001`), git commit hashes (`4ebfbe9`), CLI flags (`--use-v49`), and internal run tags (`O_v48_s0`, `fits_v47`, `carry3sh`, `Method-137`) from all prose, tables, and figure labels. Use clean participant pseudonyms (`P1`–`P6` or `TF1`–`TF6`) and descriptive scientific names.
   - **Zero Data-Cleaning / QA Diary Notes:** Replace narrative data-wrangling logs (`"Two trials had no accepted strides because the participant stood still, and three sessions had no multi-camera capture..."`) with a single standard CONSORT-style cohort accounting sentence in Methods/Results (`"From 79 recorded walking trials across 6 participants, 72 met steady-state gait screening criteria (910 strides total)."`).
   - **Mandatory Pre-Build Automated Regex Linter:** Before compiling any ISR or IEEE PDF (`./build_isr.sh` / `./build_ieee.sh`), run this automated regex check across all manuscript `.md` files and verify zero offending matches:
     ```bash
     grep -rnE \
       '(\b202[0-6]-[01][0-9]-[0-3][0-9]\b|[0-9]{4}_202[0-6][01][0-9][0-3][0-9]_[0-9]{6}|JLH000[0-9]{4}|Method[ -]137|fits_v[0-9]+|O_v4[0-9]|carry3sh|dvltqft|tf_newbase|_2026[01][0-9][0-3][0-9]\.(stl|npz|xml|json)|\b(TF|TR|KD|P0|p)[0-9]{2,3}\b|\*Status:\* PLANNED|\bTODO\b|\bTENTATIVE\b)' \
       docs/papers/<paper_slug>/*.md
     ```
5. **Gate 6 — Cross-Portfolio De-Duplication ("One Canonical Home Per Method"):**
   - Every core mathematical formulation (`ProbabilisticReconstruction` TBME 2026 pointwise Laplace marginals, `FASCIA` CT/MRI anatomy & `MhrFkOpt`, `CAMBR` multi-view front-end & `SequenceIK`, `GaitLabDataset` Pointwise Probabilistic + Implicit Kinetic Rollout `M5`) has **one primary owner manuscript**.
   - Downstream or clinical papers (`ProstheticComponentry`, `Spasticity`, `CUET`, `Tremor`, `WheelchairPropulsion`, `SARA-PULSE`, `KinTwin`) must cite the upstream foundation paper in 2–4 concise sentences and focus 100% of their Methods space on their domain-specific methodological extension—never re-deriving shared pipeline equations across multiple papers.
6. **Gate 7 — Mandatory AI Usage Acknowledgment (`acknowledgments.md`):**
   - Every 2026+ ISR manuscript must include an explicit AI usage statement in `acknowledgments.md` (or the Acknowledgments section of `manuscript.md` / `sections/acknowledgments.md`) acknowledging the use of Claude (Anthropic) and Antigravity for code development, running experiments, and manuscript preparation, and stating that the manuscript was extensively reviewed by the authors:
     > *"AI-assisted coding and research agents, including Claude (Anthropic) and Google Antigravity, were used for code development, running experiments, and assistance with manuscript preparation. The manuscript was extensively reviewed and verified by the authors, who take full responsibility for its content."*
7. **Gate 8 — Mandatory Zotero Reference & Identifier (`zotero_key`) Audit:**
   - Every `.bib` entry cited in the manuscript must carry `zotero_key = {<8-char-Zotero-key>}` verified against `http://localhost:23119/api/users/0/items/<ITEM_KEY>`. Any citation not yet in Zotero must be verified against Crossref/PubMed/arXiv for real DOI/metadata, tagged `zotero_status = {pending_user_import}`, and surfaced in a clean table of DOIs/BibTeX for the user to import into Zotero.
8. **Gate 9 — Mandatory IEEE Font Compliance (`pdf.fonttype = 42`, Zero Type 3 Bitmap Fonts, & `pdffonts` Audit):**
   - IEEE Xplore / PDF eXpress strictly rejects **Type 3 bitmap fonts** (which Matplotlib emits by default when `pdf.fonttype = 3`) as well as non-embedded fonts (`emb = no`).
   - Every Matplotlib figure script must explicitly configure:
     ```python
     plt.rcParams.update({
         "pdf.fonttype": 42,          # Embed TrueType (Type 42) outlines — NEVER Type 3 (3)
         "ps.fonttype": 42,           # Embed TrueType in PostScript/EPS
         "svg.fonttype": "none",      # Keep text as <text> elements using standard installed serif fonts
         "font.family": "serif",
         "font.serif": ["Times New Roman", "Liberation Serif", "DejaVu Serif"],
         "mathtext.fontset": "stix",  # STIX vector math glyphs (avoids Type 3 Computer Modern bitmaps)
         "text.usetex": False,        # Avoid dvipng/Type 3 TeX bitmap fallbacks
     })
     ```
   - Both `./build_isr.sh` and `./build_ieee.sh` must run `pdffonts <output>.pdf` after compilation and fail the build if any font has `type == "Type 3"` or `emb == "no"`.

### Cycle 5 — SVG-First Tufte Serif Figures, Inkscape PDF Pipeline, TikZ Policy, & Redline Diff PDF
1. **SVG-First Figure Generation (`scripts/generate_paper_figures.py`) & TikZ Preservation Policy:**
   - **Generate `.svg` + `.pdf` + `.png` for all programmatic figures:** Save every Matplotlib / programmatic figure in all three formats (`fig.savefig(f"{stem}.svg", transparent=True, bbox_inches="tight")`, `.pdf`, and 300 DPI `.png`).
   - **Reference `.svg` in MyST Markdown (`![](figures/fig_name.svg)`):** Referencing `.svg` in `.md` files gives crisp, infinitely zoomable vector rendering in **MyST Studio (`http://127.0.0.1:7319`)** and HTML builds, while MyST's LaTeX/PDF exporter automatically converts `.svg -> .pdf` via `inkscape` (or our lightweight `~/.local/bin/inkscape` CLI wrapper around `rsvg-convert -f pdf`) during `./build_isr.sh` and `./build_ieee.sh`.
   - **Keep Existing TikZ Diagrams as `.tikz.tex` / `.pdf` (Do Not Convert TikZ $\to$ SVG):** Standalone or inline TikZ schematics (`*.tikz.tex` compiled directly by `pdflatex` to `.pdf` + `.png` for web preview) are already native LaTeX vector graphics with Type 1/TrueType fonts. Converting `TikZ -> PDF -> SVG -> Inkscape -> PDF` introduces unnecessary double-conversion and can degrade math glyph embeddings or clipping boxes—leave TikZ diagrams untouched as `.tikz.tex`/`.pdf`.
   - Use serif typography (`Times New Roman` / `Liberation Serif` / `DejaVu Serif`, `mathtext.fontset = "stix"`, `pdf.fonttype = 42`) with mathematical symbols identical to `methods.md`.
   - Use left-aligned 2-line panel headers (**bold** panel letter + claim on line 1; muted `#475569` subtitle with $N$, units, and statistic on line 2), despined top/right axes, and `1:1` native pixel aspect ratios (`aspect="equal"`) on all camera crops and 3D renders.
2. **Dual ISR & IEEE Compilation + `pdffonts` Audit + Page-by-Page Visual Inspection:**
   - Run `./build_isr.sh` and `./build_ieee.sh` (ensuring `inkscape` or the `rsvg-convert` `inkscape` shim is on `PATH`), verify `pdffonts` reports **zero `Type 3` fonts** and **100% `emb = yes`**, render pages to PNG (`pdftoppm -png -r 150 <paper>_isr.pdf page`), and visually inspect every page (or preview live in **Sheprd MyST Studio** via `./sheprd myst` on `http://127.0.0.1:7319`).
3. **Word-Level Redline Diff PDF (`scripts/diff_commits_pdf.py`):**
   - Whenever completing an editing cycle or preparing a revision for co-author review, generate a publication-style inline word-diff PDF comparing the baseline commit/tag against the updated manuscript:
     ```bash
     python scripts/diff_commits_pdf.py <baseline_commit_or_tag> WORKTREE -f manuscript.md -o exports/manuscript_diff.pdf
     ```

### Cycle 6 — Addressing Inline MyST Studio Comments (`status: "addressed"`) & Finalization (`myst-paper-finalize`)
1. **Never Delete `<!-- tandem-comments -->` Blocks While Addressing Review Comments:**
   - When addressing inline user comments stored in `<!-- tandem-comments ... -->` at the bottom of `.md` files (or queried via `./sheprd myst-comments <paper_id>`), **never strip or delete the comment entries during iterative drafting**.
   - Instead, update each addressed comment entry in-place inside `<!-- tandem-comments -->` so MyST Studio renders an emerald-green addressed highlight (`✓💬`) over the revised prose together with your explanation:
     - Set `"status": "addressed"` and `"resolved": true`.
     - Preserve the original highlighted text in `"originalQuote"`.
     - Update `"quote"` to a verbatim substring (`60–180` characters) of the **newly rewritten sentence** in that `.md` file so the highlight attaches cleanly in Live Paper and RTF views.
     - Set `"addressedBy"` (e.g., `"claude-pb124-fascia-flow (eqx w6:p3)"`), `"addressedAt"` (`"YYYY-MM-DD HH:MM"`), and `"agentReply"` (concise 1–3 sentence explanation of the prose/figure change and any literature or metric verification).
2. **Finalizing and Stripping Comment History (`myst-paper-finalize`):**
   - Only strip `<!-- tandem-comments -->` history when the user explicitly asks to clear addressed comments or finalize the manuscript for submission (see [`.agents/skills/myst-paper-finalize/SKILL.md`](file:///Users/jcotton/projects/herdr-herding/.agents/skills/myst-paper-finalize/SKILL.md)):
     ```bash
     ./sheprd myst-comments <paper_id>                      # Inspect open & addressed comments
     ./sheprd myst-comments finalize <paper_id> --addressed # Strip only addressed comments
     ./sheprd myst-comments finalize <paper_id> --all       # Strip all comment history for submission
     ```
