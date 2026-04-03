---
name: semi-formal-code-reasoning
description: >
  Structured semi-formal reasoning templates for agentic code analysis. Use this skill whenever Claude
  is asked to reason deeply about code semantics without executing it — including: comparing two patches
  or code changes for equivalence, reviewing pull requests or diffs for correctness, localizing bugs
  or faults from failing tests, answering questions about how code behaves across a repository,
  verifying refactors preserve behavior, or any task where Claude must trace execution paths through
  multi-file codebases. Trigger on phrases like "are these patches equivalent", "review this diff",
  "find the bug", "why does this test fail", "does this refactor change behavior", "trace through this
  code", "what does this code actually do", or any code analysis task spanning multiple files where
  getting the reasoning right matters. Also trigger when the user asks Claude to act as a code verifier,
  reward model, or static analyzer. Do NOT use for simple syntax questions, formatting, or code generation
  tasks where execution tracing is unnecessary.
---

# Semi-Formal Code Reasoning

This skill implements structured reasoning templates that force explicit evidence gathering before
conclusions. Based on research showing 10+ percentage point accuracy gains over unstructured
chain-of-thought on patch equivalence, fault localization, and code question answering tasks.

> **Reference:** Ugare, Shubham, and Satish Chandra. 2026. "Agentic Code Reasoning."
> arXiv:2603.01896. Preprint, arXiv, March 4. https://doi.org/10.48550/arXiv.2603.01896.

## Core Principle

**Never conclude without tracing.** The central failure mode in code reasoning is assuming behavior
from names, signatures, or surface similarity. Semi-formal reasoning prevents this by requiring a
certificate: explicit premises, concrete execution traces with file:line evidence, and a formal
conclusion that follows from the traces. If you can't fill in the template, you haven't gathered
enough evidence yet.

## When to Use Which Template

| Task | Template | Trigger |
|------|----------|---------|
| Comparing two patches/diffs | **Patch Equivalence** | "are these equivalent", "same behavior", PR review with alternatives |
| Finding buggy code from test failures | **Fault Localization** | "find the bug", "why does this fail", "localize the fault" |
| Understanding code behavior | **Code QA** | "what does this do", "how does X work", "trace through this" |
| General code review | **Code Review** (adapted from Patch Equivalence) | "review this PR", "is this change safe" |

Pick the closest template. For ambiguous tasks, Code QA is the most general.

---

## Template 1: Patch Equivalence

Use when comparing two code changes to determine if they produce the same behavior.

### Structured Exploration Phase

Before filling the certificate, gather evidence systematically:

1. **Read both patches carefully.** Identify every file and function touched.
2. **For each function called in the patches:**
   - Search for its definition in the repository (do NOT assume standard library semantics —
     names can be shadowed by module-level or project-specific definitions).
   - Document: `FUNCTION: name | LOCATION: file:line | ACTUAL BEHAVIOR: ...`
3. **Read the test patch** (if available). Identify what behaviors are tested.
4. **Check for side effects:** imports, module-level definitions, class inheritance, decorators,
   middleware, signal handlers — anything that could alter execution semantics.

### Certificate Template

```
DEFINITIONS:
  D1: Two patches are EQUIVALENT MODULO TESTS iff executing the
      repository test suite produces identical pass/fail outcomes.
  D2: The relevant tests are ONLY those in FAIL_TO_PASS and
      PASS_TO_PASS (the existing test suite).

PREMISES (state what each patch does — cite file:line):
  P1: Patch 1 modifies [file(s)] by [specific change, with line refs]
  P2: Patch 2 modifies [file(s)] by [specific change, with line refs]
  P3: The FAIL_TO_PASS tests check [specific behavior]
  P4: The PASS_TO_PASS tests check [specific behavior, if relevant]

FUNCTION RESOLUTION TABLE:
  | Function/Symbol | Assumed Meaning | Actual Definition (file:line) | Different? |
  |-----------------|-----------------|-------------------------------|------------|
  (Fill for EVERY function/method called in either patch)

ANALYSIS OF TEST BEHAVIOR:
  For each FAIL_TO_PASS test:
    Claim 1.1: With Patch 1, test [name] will [PASS/FAIL]
               because [concrete execution trace through code]
    Claim 1.2: With Patch 2, test [name] will [PASS/FAIL]
               because [concrete execution trace through code]
    Comparison: [SAME/DIFFERENT] outcome

  For each relevant PASS_TO_PASS test:
    Claim 2.1: With Patch 1, behavior is [description with trace]
    Claim 2.2: With Patch 2, behavior is [description with trace]
    Comparison: [SAME/DIFFERENT] outcome

EDGE CASES (only those exercised by actual tests):
  E1: [Edge case] → Patch 1: [behavior] | Patch 2: [behavior] | Same? [Y/N]

COUNTEREXAMPLE (if NOT EQUIVALENT):
  Test [name] will [PASS/FAIL] with Patch 1 because [traced reason]
  Test [name] will [FAIL/PASS] with Patch 2 because [traced reason]

  OR

NO COUNTEREXAMPLE EXISTS (if EQUIVALENT):
  All tests produce identical outcomes because [traced reason]

FORMAL CONCLUSION:
  By D1, since test outcomes are [IDENTICAL/DIFFERENT],
  patches are [EQUIVALENT / NOT EQUIVALENT].

ANSWER: [YES/NO]
CONFIDENCE: [HIGH/MEDIUM/LOW] — [brief justification]
```

### Key Anti-Patterns to Avoid

- **Name assumption:** Never assume `format()`, `open()`, `print()`, etc. are builtins.
  Always check for module-level shadowing.
- **Skipping tests:** Trace EVERY test, not just the ones that look relevant.
- **Surface similarity:** High textual similarity does NOT imply semantic equivalence.
  Patches can look identical but diverge on one edge case.
- **Premature conclusion:** If you find yourself writing the ANSWER before completing
  the ANALYSIS section, stop and go back.

---

## Template 2: Fault Localization

Use when finding buggy code given a failing test, without execution information.

### Structured Exploration Phase

Explore in a hypothesis-driven loop:

```
HYPOTHESIS H[N]: [What you expect to find and why it may contain the bug]
EVIDENCE: [What from the test or previously read files supports this]
CONFIDENCE: [high/medium/low]

-> Read the file

OBSERVATIONS from [filename]:
  O[N]: [Key observation, with line numbers]

HYPOTHESIS UPDATE:
  H[M]: [CONFIRMED | REFUTED | REFINED] — [Explanation]

UNRESOLVED:
  - [What questions remain]

NEXT ACTION RATIONALE: [Why reading another file, or why enough evidence]
```

### Certificate Template

```
## Phase 1: Test Semantics Analysis

PREMISE T1: The test calls [X.method(args)] and expects [behavior]
PREMISE T2: The test asserts [condition]
PREMISE T3: [Additional test constraints]

Key question: What is the EXPECTED vs OBSERVED behavior?

## Phase 2: Code Path Tracing

Trace from test entry point into production code:

  METHOD: [ClassName.methodName(params)]
  LOCATION: [file:line]
  BEHAVIOR: [what this method does — VERIFIED by reading source]
  RELEVANT: [why it matters to the test]

  -> [next call in chain]
  ...

## Phase 3: Divergence Analysis

For each traced path, identify where implementation diverges from expectations:

  CLAIM D1: At [file:line], [code] would produce [behavior]
            which contradicts PREMISE T[N] because [reason]
  CLAIM D2: ...

Each claim MUST reference a specific PREMISE and specific code location.

IMPORTANT — Distinguish ROOT CAUSE from CRASH SITE:
  - The crash site is where the error manifests (e.g., StackOverflowError)
  - The root cause is the code that creates the bad state
  - Always trace BACKWARD from crash site to root cause

## Phase 4: Ranked Predictions

  Rank 1 ([confidence]): [file:lines] — [root cause description]
    Supporting claims: D[N], D[M]
  Rank 2 ([confidence]): [file:lines] — [description]
    Supporting claims: D[N]
  ...up to Rank 5
```

### Key Anti-Patterns to Avoid

- **Stopping at the crash site:** The method that throws the exception is usually NOT
  the root cause. Trace backward to find what created the bad state.
- **Single-turn predictions:** Don't predict from test code alone. Read source files.
- **Name-based guessing:** Don't assume a method is buggy because its name is similar
  to the failing test. Trace the actual execution path.
- **Ignoring indirection:** Bugs are often in configuration classes, factory methods, or
  helper utilities — not in the method directly called by the test.

---

## Template 3: Code Question Answering

Use when answering questions about code behavior, semantics, or design.

### Certificate Template

```
FUNCTION TRACE TABLE:
  | Function/Method | File:Line | Parameter Types | Return Type | Behavior (VERIFIED) |
  |-----------------|-----------|-----------------|-------------|---------------------|
  (Every function examined — MUST read source, not guess from name)

DATA FLOW ANALYSIS:
  Variable: [key variable name]
  - Created at: [file:line]
  - Modified at: [file:line(s), or 'NEVER MODIFIED']
  - Used at: [file:line(s)]
  (Repeat for each key variable relevant to the question)

SEMANTIC PROPERTIES:
  Property 1: [e.g., "HashMap is mutable", "this list is sorted"]
  - Evidence: [specific file:line]
  Property 2: ...

ALTERNATIVE HYPOTHESIS CHECK:
  If the opposite answer were true, what evidence would exist?
  - Searched for: [what you looked for]
  - Found: [what you found — cite file:line]
  - Conclusion: [REFUTED / SUPPORTED]

ANSWER: [Final answer with explicit evidence chain]
CONFIDENCE: [HIGH/MEDIUM/LOW]
```

### Key Anti-Patterns to Avoid

- **Answering from function names:** `getUserName()` might not return a user's name.
  Read the implementation.
- **Missing downstream handling:** Even if you find an edge case, check whether
  downstream code already handles it before claiming it's a problem.
- **Incomplete trace chains:** If your answer depends on 5 functions, trace all 5.
  A chain is only as strong as its weakest link.

---

## Template 4: Code Review (Adapted)

Use for general PR/diff review when there's no second patch to compare against.

### Certificate Template

```
CHANGE SUMMARY:
  C1: [file] line [N-M]: [what changed and why, based on PR description]
  C2: ...

FUNCTION RESOLUTION TABLE:
  | Function/Symbol | Called In Change? | Definition (file:line) | Semantics Verified? |
  |-----------------|-------------------|------------------------|---------------------|

BEHAVIORAL ANALYSIS:
  For each change C[N]:
    - Pre-change behavior: [traced from code]
    - Post-change behavior: [traced from code]
    - Regression risk: [NONE / LOW / MEDIUM / HIGH] — [specific reason]

INVARIANT CHECK:
  For each invariant or assumption the code relies on:
    I1: [invariant] — PRESERVED / BROKEN by change C[N] because [reason]

EDGE CASES:
  E1: [input/state] -> Pre: [behavior] | Post: [behavior] | Safe? [Y/N]

CONCLUSION:
  [APPROVE / REQUEST CHANGES / NEEDS DISCUSSION]
  Summary: [1-2 sentence summary of findings]
  Issues found: [list, or "none"]
```

---

## General Guidance

### Calibrating Depth

Not every analysis needs the full template. Use judgment:

- **Quick check** (high-confidence, small diff, single file): Fill the template mentally,
  write a condensed version. ~5 minutes equivalent.
- **Standard analysis** (moderate complexity, 2-5 files): Full template, moderate exploration.
  ~15-30 agent steps.
- **Deep analysis** (subtle semantics, cross-module dependencies, framework-specific behavior):
  Full template with extensive exploration. ~30-50 agent steps.

If the user asks for a quick review, provide a condensed version but flag if you spot
something that warrants deeper analysis.

### When Semi-Formal Reasoning Helps Most

The accuracy gains are largest when:
- Code spans multiple files with non-obvious dependencies
- Functions or symbols might be shadowed or overridden
- The difference between correct and incorrect hinges on a subtle semantic detail
- Framework-specific behavior differs from standard library behavior
- Multiple test cases need to be reasoned about independently

### When It Helps Less

- Single-file, self-contained code snippets
- Pure syntax or formatting questions
- Cases where the model already has strong baseline accuracy
- When speed matters more than thoroughness (flag the tradeoff to the user)

### Running Independent Probes

When you cannot execute repository code but need to verify language semantics (e.g., "what
does Python's `format()` builtin do with this input?"), you may write and run small
independent scripts that test general language behavior. This is legitimate static analysis —
you are verifying your understanding of the language, not executing the repository's code.

### Presenting Results

After completing the certificate:
1. **Lead with the answer** — don't make the user read the whole trace first.
2. **Summarize key findings** in 2-3 sentences.
3. **Offer the full certificate** as supporting evidence if the user wants to audit
   your reasoning.
4. **Flag confidence level** and explain what would change your mind.
