#!/usr/bin/env bash
# Build the IEEE two-column manuscript (paper_ieee.pdf): MyST -> pdflatex + Biber -> pdflatex x 2.
set -euo pipefail
cd "$(dirname "$0")"

PAPER_STEM="${1:-paper_ieee}"

myst build --tex manuscript.md

cp -f templates/ieeetrans/IEEEtran.cls .

if [ -f references.bib ]; then
  cp -f references.bib main.bib
fi

pdflatex -interaction=nonstopmode "${PAPER_STEM}.tex" >/dev/null || true
biber "${PAPER_STEM}" >/dev/null || true
pdflatex -interaction=nonstopmode "${PAPER_STEM}.tex" >/dev/null || true
pdflatex -interaction=nonstopmode "${PAPER_STEM}.tex" 2>&1 | tail -5 || true

if grep -qE 'Citation.*undefined|There were undefined references|could not be found' "${PAPER_STEM}.log"; then
  echo "ERROR: unresolved citations or references remain in ${PAPER_STEM}.pdf" >&2
  grep -E 'Citation.*undefined|Reference.*undefined' "${PAPER_STEM}.log" >&2 || true
  exit 1
fi

echo "Built ${PAPER_STEM}.pdf successfully."
