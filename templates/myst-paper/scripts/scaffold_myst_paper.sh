#!/usr/bin/env bash
# Scaffold a new ISR + IEEE MyST paper directory from the canonical RAE myst-paper template.
# Usage: ./scaffold_myst_paper.sh <target_dir> ["Paper Title"] [paper_slug]
set -euo pipefail

if [ $# -lt 1 ]; then
  echo "Usage: $0 <target_dir> [\"Paper Title\"] [paper_slug]" >&2
  exit 1
fi

TARGET_DIR="$1"
PAPER_TITLE="${2:-Paper Title: Replace with Clear, Jargon-Free Scientific Title}"
PAPER_SLUG="${3:-$(basename "$TARGET_DIR")}"
TEMPLATE_DIR="$(cd "$(dirname "$0")/.." && pwd)"

mkdir -p "$TARGET_DIR"
cp -rn "$TEMPLATE_DIR/"* "$TARGET_DIR/" 2>/dev/null || true
cp -rn "$TEMPLATE_DIR/.gitignore" "$TARGET_DIR/.gitignore" 2>/dev/null || true
chmod +x "$TARGET_DIR/build_isr.sh" "$TARGET_DIR/build_ieee.sh" "$TARGET_DIR/scripts/diff_commits_pdf.py" "$TARGET_DIR/scripts/audit_zotero_bib.py" "$TARGET_DIR/scripts/ensure_inkscape_and_check_fonts.py" "$TARGET_DIR/scripts/generate_paper_figures.py" 2>/dev/null || true

python3 - "$TARGET_DIR" "$PAPER_TITLE" "$PAPER_SLUG" <<'PY'
from pathlib import Path
import sys

target_dir = Path(sys.argv[1])
title = sys.argv[2]
slug = sys.argv[3]

for fname in ("myst.yml", "manuscript.md"):
    p = target_dir / fname
    if p.exists():
        text = p.read_text(encoding="utf-8")
        text = text.replace("Paper Title: Replace with Clear, Jargon-Free Scientific Title", title)
        text = text.replace("paper_isr", f"{slug}_isr").replace("paper_ieee", f"{slug}_ieee")
        p.write_text(text, encoding="utf-8")

for bscript, suffix in (("build_isr.sh", f"{slug}_isr"), ("build_ieee.sh", f"{slug}_ieee")):
    p = target_dir / bscript
    if p.exists():
        text = p.read_text(encoding="utf-8")
        text = text.replace("paper_isr", suffix).replace("paper_ieee", suffix)
        p.write_text(text, encoding="utf-8")
PY

echo "Scaffolded MyST paper in $TARGET_DIR (outputs: ${PAPER_SLUG}_isr.pdf, ${PAPER_SLUG}_ieee.pdf)"
