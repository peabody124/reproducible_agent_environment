#!/usr/bin/env python3
"""Canonical Tufte + IEEE-compliant figure generator for RAE MyST manuscripts.

Key standards enforced by this module:
1. Primary format for MyST Markdown is `.svg` (`![](figures/fig_name.svg)`), saved alongside
   `.pdf` (vector archival) and `.png` (300 DPI raster preview) via `save_paper_figure()`.
   Why: `.svg` renders natively as crisp scalable vector graphics in MyST Markdown and MyST
   Studio web previews, while MyST (`myst build --tex` / `myst build --pdf`) converts
   `.svg -> .pdf` via `inkscape` during LaTeX compilation.
2. Zero Type 3 bitmap fonts (IEEE PDF eXpress compliance):
   Matplotlib defaults to `pdf.fonttype = 3` and `ps.fonttype = 3` (Type 3 bitmap fonts, which
   IEEE PDF eXpress rejects). `TUFTE_IEEE_RC` sets `pdf.fonttype = 42`, `ps.fonttype = 42`,
   `svg.fonttype = "none"`, `mathtext.fontset = "stix"`, and `text.usetex = False`.
3. Existing standalone/inline TikZ diagrams (`.tikz.tex` / `.pdf`) should be kept untouched
   for LaTeX compilation; use `.svg` for all programmatic Python/Matplotlib/vector figures.
"""

from __future__ import annotations

import argparse
from collections.abc import Sequence
from pathlib import Path

import matplotlib as mpl
import matplotlib.pyplot as plt
import numpy as np

TUFTE_IEEE_RC: dict[str, object] = {
    # Serif typography matching ISR & IEEE body text
    "font.family": "serif",
    "font.serif": ["Times New Roman", "Liberation Serif", "DejaVu Serif"],
    "font.size": 10,
    # STIX math fontset — never use text.usetex=True (which can emit Type 3 PK bitmap fonts)
    "mathtext.fontset": "stix",
    "text.usetex": False,
    # IEEE PDF eXpress compliance: TrueType Type 42 outlines (NEVER Matplotlib's default Type 3!)
    "pdf.fonttype": 42,
    "ps.fonttype": 42,
    # Keep SVG text as selectable <text> elements so MyST web previews & rsvg-convert embed clean fonts
    "svg.fonttype": "none",
    # Transparent backgrounds so figures blend into ISR cream/white & IEEE two-column pages
    "figure.facecolor": "none",
    "axes.facecolor": "none",
    "savefig.facecolor": "none",
    "savefig.transparent": True,
    "savefig.bbox": "tight",
    "savefig.pad_inches": 0.12,
    # Tufte despined axes & subtle inward ticks
    "axes.edgecolor": "#333333",
    "axes.linewidth": 0.6,
    "axes.spines.top": False,
    "axes.spines.right": False,
    "axes.grid": False,
    "xtick.direction": "in",
    "ytick.direction": "in",
    "xtick.major.size": 3,
    "ytick.major.size": 3,
    "xtick.major.width": 0.5,
    "ytick.major.width": 0.5,
    "legend.frameon": False,
}


def configure_tufte_ieee_matplotlib() -> None:
    """Apply canonical Tufte + IEEE Type-42 font settings and sync STIX fonts for SVG->PDF."""
    mpl.rcParams.update(TUFTE_IEEE_RC)
    try:
        from ensure_inkscape_and_check_fonts import sync_matplotlib_stix_fonts

        sync_matplotlib_stix_fonts()
    except ImportError:
        pass


def save_paper_figure(
    fig: mpl.figure.Figure,
    stem_or_path: str | Path,
    formats: Sequence[str] = ("svg", "pdf", "png"),
    dpi: int = 300,
) -> list[Path]:
    """Save a figure as `.svg` (primary for MyST `.md`), `.pdf`, and `.png` with transparent bg."""
    base = Path(stem_or_path)
    if base.suffix.lower() in {".svg", ".pdf", ".png"}:
        base = base.with_suffix("")
    base.parent.mkdir(parents=True, exist_ok=True)

    written: list[Path] = []
    for fmt in formats:
        ext = fmt.lstrip(".").lower()
        out = base.with_suffix(f".{ext}")
        fig.savefig(out, format=ext, dpi=dpi, transparent=True, bbox_inches="tight")
        written.append(out)
    return written


def generate_demo_figure(figures_dir: Path) -> list[Path]:
    """Generate a verification figure exercising STIX math, serif typography, and Tufte axes."""
    configure_tufte_ieee_matplotlib()
    fig, ax = plt.subplots(figsize=(6.0, 3.6))

    x = np.linspace(0.0, 100.0, 200)
    y_mean = 18.0 * np.exp(-x / 35.0) + 4.2
    y_ci = 2.4 * np.exp(-x / 50.0) + 0.6

    ax.fill_between(x, y_mean - y_ci, y_mean + y_ci, color="#4e79a7", alpha=0.18, linewidth=0)
    ax.plot(x, y_mean, color="#4e79a7", linewidth=1.8)
    ax.axhline(4.2, color="#666666", linestyle="--", linewidth=0.8)

    ax.text(
        101.5,
        y_mean[-1],
        r"Calibrated $\mathcal{L}_{\mathrm{NLL}}(\boldsymbol{\theta}, \boldsymbol{\beta})$",
        fontsize=9.5,
        color="#4e79a7",
        va="center",
    )
    ax.set_xlim(0.0, 100.0)
    ax.set_ylim(0.0, 24.0)
    ax.spines["bottom"].set_bounds(0.0, 100.0)
    ax.spines["left"].set_bounds(0.0, 24.0)

    ax.set_xlabel(r"Gait CycleNormalized Time $t$ (%) — $\Delta\mathrm{BIC} = -42.1$, $\alpha = 0.05$")
    ax.set_ylabel(r"Joint Tracking Error $\sum_{i=1}^{N} \|x_i - \hat{x}_i\|_2$ (mm)")
    ax.set_title(
        r"A. Calibrated Trajectory Optimization Reduces Tracking Error ($14.2 \pm 0.8\;\mathrm{mm}$)",
        loc="left",
        fontsize=10.5,
        fontweight="bold",
        pad=10,
    )

    written = save_paper_figure(fig, figures_dir / "fig_sample_tufte")
    plt.close(fig)
    return written


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate publication figures (.svg, .pdf, .png).")
    parser.add_argument(
        "--figures-dir",
        type=Path,
        default=Path(__file__).resolve().parent.parent / "figures",
        help="Destination directory for generated manuscript figures.",
    )
    parser.add_argument(
        "--demo",
        action="store_true",
        help="Generate a sample Tufte + STIX math figure to verify SVG->PDF and Type-42 font embedding.",
    )
    args = parser.parse_args()

    configure_tufte_ieee_matplotlib()
    if args.demo:
        written = generate_demo_figure(args.figures_dir)
        print("Generated demo figure files:", ", ".join(str(p) for p in written))
    else:
        args.figures_dir.mkdir(parents=True, exist_ok=True)
        print(f"Configured TUFTE_IEEE_RC (pdf.fonttype=42, svg.fonttype='none'). Target: {args.figures_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
