# Reproducing the Results & Building the Paper

Record the exact git commit, branch, and commands used to generate every table, figure, and PDF in this manuscript.

| Build | Commit | Branch | Date | Notes |
| :--- | :--- | :--- | :--- | :--- |
| Initial scaffold | `TODO` | `main` | `YYYY-MM-DD` | Scaffolded from RAE `templates/myst-paper` |

## 1. Regenerate Figures & Tables

```bash
CUDA_VISIBLE_DEVICES=0 python scripts/generate_paper_figures.py
```

## 2. Build ISR Single-Column Preprint & IEEE Two-Column PDF

```bash
./build_isr.sh
./build_ieee.sh
```

## 3. Generate Word-Level Redline Diff PDF Between Revisions

```bash
python scripts/diff_commits_pdf.py HEAD~1 WORKTREE -f manuscript.md -o exports/manuscript_diff.pdf
```
