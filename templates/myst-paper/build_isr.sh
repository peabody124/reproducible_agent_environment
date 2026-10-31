#!/usr/bin/env bash
# Build the ISR preprint (paper_isr.pdf): MyST -> XeLaTeX + Biber -> XeLaTeX x 2.
# The ISR template (templates/isr, isrpaper.cls) uses fontspec (requires XeTeX, NOT pdflatex)
# and biblatex with the biber backend (NOT bibtex).
set -euo pipefail
cd "$(dirname "$0")"

PAPER_STEM="${1:-paper_isr}"

myst build --tex manuscript.md

# Ensure isrpaper.cls and isr-logo.pdf are available in the working directory for XeLaTeX
cp -f templates/isr/isrpaper.cls templates/isr/isr-logo.pdf .

# MyST culls main.bib to the citations of the doc it built last; overwrite with full references.bib
if [ -f references.bib ]; then
  cp -f references.bib main.bib
fi

xelatex -interaction=nonstopmode "${PAPER_STEM}.tex" >/dev/null || true
biber "${PAPER_STEM}" >/dev/null || true
xelatex -interaction=nonstopmode "${PAPER_STEM}.tex" >/dev/null || true
xelatex -interaction=nonstopmode "${PAPER_STEM}.tex" 2>&1 | tail -5 || true

# Fail loudly if any \cite stayed unresolved (biblatex renders those as bold "?")
if grep -qE 'Citation.*undefined|There were undefined references|could not be found' "${PAPER_STEM}.log"; then
  echo "ERROR: unresolved citations or references remain in ${PAPER_STEM}.pdf" >&2
  grep -E 'Citation.*undefined|Reference.*undefined' "${PAPER_STEM}.log" >&2 || true
  exit 1
fi

echo "Built ${PAPER_STEM}.pdf successfully."
