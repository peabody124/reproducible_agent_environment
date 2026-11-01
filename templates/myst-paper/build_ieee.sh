#!/usr/bin/env bash
# Build the IEEE two-column conference manuscript (paper_ieee.pdf) on ieeeconf.cls:
# MyST -> XeLaTeX + Biber -> XeLaTeX x 2 (XeLaTeX, like the ISR build, for Unicode text).
set -euo pipefail
cd "$(dirname "$0")"

PAPER_STEM="${1:-paper_ieee}"
export PATH="$HOME/.local/bin:$PATH"

if [ -f scripts/ensure_inkscape_and_check_fonts.py ]; then
  python3 scripts/ensure_inkscape_and_check_fonts.py --ensure-inkscape
fi

myst build --tex manuscript.md

cp -f templates/ieeeconf/ieeeconf.cls .

if [ -f references.bib ]; then
  cp -f references.bib main.bib
fi

xelatex -interaction=nonstopmode "${PAPER_STEM}.tex" >/dev/null || true
biber "${PAPER_STEM}" >/dev/null || true
xelatex -interaction=nonstopmode "${PAPER_STEM}.tex" >/dev/null || true
xelatex -interaction=nonstopmode "${PAPER_STEM}.tex" 2>&1 | tail -5 || true

if [ ! -f "${PAPER_STEM}.pdf" ] || [ ! -f "${PAPER_STEM}.log" ]; then
  echo "ERROR: ${PAPER_STEM}.pdf was not built (see the myst and xelatex output above)" >&2
  exit 1
fi

if grep -qE 'Citation.*undefined|There were undefined references|could not be found' "${PAPER_STEM}.log"; then
  echo "ERROR: unresolved citations or references remain in ${PAPER_STEM}.pdf" >&2
  grep -E 'Citation.*undefined|Reference.*undefined' "${PAPER_STEM}.log" >&2 || true
  exit 1
fi

# Verify IEEE/publisher font compliance: 0 Type 3 bitmap fonts, 100% embedded fonts
if [ -f scripts/ensure_inkscape_and_check_fonts.py ]; then
  python3 scripts/ensure_inkscape_and_check_fonts.py --check-pdf "${PAPER_STEM}.pdf"
fi

echo "Built ${PAPER_STEM}.pdf successfully."
