---
title: "Paper Title: Replace with Clear, Jargon-Free Scientific Title"
author:
  - name: R. James Cotton
    affiliations:
      - Shirley Ryan AbilityLab
      - Department of Physical Medicine and Rehabilitation, Northwestern University
    orcid: 0000-0001-5714-1400
    email: rcotton@sralab.org
license: CC-BY-4.0
keywords:
  - rehabilitation
  - biomechanics
  - markerless motion capture
bibliography:
  - references.bib
exports:
  # Primary ISR lab single-column preprint target (cream header box, green ORCID, author-year citations)
  - format: pdf
    template: ./templates/isr
    output: paper_isr.pdf
    paper_date: "October 2026"
    correspondence: "rcotton@sralab.org"
  - format: tex
    template: ./templates/isr
    output: paper_isr.tex
    paper_date: "October 2026"
    correspondence: "rcotton@sralab.org"
  # Secondary IEEE two-column submission target from the exact same MyST Markdown sources
  - format: pdf
    template: ./templates/ieeetrans
    output: paper_ieee.pdf
  - format: tex
    template: ./templates/ieeetrans
    output: paper_ieee.tex
---

+++ {"part": "abstract"}

```{include} abstract.md
```

+++

```{include} introduction.md
```

```{include} methods.md
```

```{include} results.md
```

```{include} discussion.md
```

```{include} acknowledgments.md
```

```{include} appendix.md
```
