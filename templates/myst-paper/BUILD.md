# Reproducing the Results & Building the Paper

Record the exact git commit, branch, and commands used to generate every table, figure, and PDF in this manuscript.

| Build | Commit | Branch | Date | Notes |
| :--- | :--- | :--- | :--- | :--- |
| Initial scaffold | `TODO` | `main` | `YYYY-MM-DD` | Scaffolded from RAE `templates/myst-paper` |

## 1. Regenerate Figures & Tables

All programmatic figures (`scripts/generate_paper_figures.py`) are saved as **`.svg` (primary format referenced in MyST `.md` files)** alongside `.pdf` and `.png`, with `pdf.fonttype = 42`, `ps.fonttype = 42`, `svg.fonttype = "none"`, and `mathtext.fontset = "stix"` so zero Type 3 bitmap fonts are ever emitted. Existing standalone/inline TikZ diagrams remain untouched as `.tikz.tex` / `.pdf`.

```bash
CUDA_VISIBLE_DEVICES=0 python3 scripts/generate_paper_figures.py
```

## 2. Build ISR Single-Column Preprint & IEEE Two-Column PDF

`./build_isr.sh` and `./build_ieee.sh` automatically invoke `scripts/ensure_inkscape_and_check_fonts.py` to:
1. Ensure `inkscape` (or a zero-GUI `rsvg-convert -f pdf` CLI shim + Fontconfig-indexed Matplotlib STIX TrueType fonts) is available on `PATH` for MyST `.svg -> .pdf` conversion.
2. Run `pdffonts` after `xelatex` compilation and fail the build if any `Type 3` bitmap font or unembedded font (`emb = no`) is present.

```bash
./build_isr.sh
./build_ieee.sh
```

## 3. Generate Word-Level Redline Diff PDF Between Revisions

```bash
python scripts/diff_commits_pdf.py HEAD~1 WORKTREE -f manuscript.md -o exports/manuscript_diff.pdf
```
