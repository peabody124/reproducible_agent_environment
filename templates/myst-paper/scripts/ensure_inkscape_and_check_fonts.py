#!/usr/bin/env python3
"""Ensure an Inkscape-compatible SVG->PDF CLI + STIX fonts are installed, and audit PDFs for Type 3 / unembedded fonts.

Why this exists:
1. MyST (`myst build --tex` / `myst build --pdf`) converts `.svg` figures to `.pdf` by calling:
     inkscape <input.svg> --export-area-drawing --export-type=pdf --export-filename=<output.pdf>
   In headless GPU/CPU containers where the heavy GUI `inkscape` package is absent, this script
   installs a lightweight, zero-GUI `~/.local/bin/inkscape` shim backed by `rsvg-convert` (from
   `librsvg2-bin`, or `ctypes` `librsvg-2.so.2` + `libcairo.so.2`).
2. Matplotlib's `mathtext.fontset = "stix"` references `STIXGeneral` and `STIXNonUnicode` fonts
   bundled inside `matplotlib/mpl-data/fonts/ttf/`. Syncing those `.ttf` files into
   `~/.local/share/fonts/matplotlib/` allows Fontconfig (`rsvg-convert` / `inkscape`) to embed the
   exact STIX math glyphs as TrueType/CID fonts when converting `.svg -> .pdf`.
3. IEEE PDF eXpress strictly rejects PDFs containing Type 3 bitmap fonts (`Type 3`) or unembedded
   fonts (`emb = no`). Running `--check-pdf <paper>.pdf` parses `pdffonts` output and fails the
   build loudly if any `Type 3` or unembedded font is present.
"""

from __future__ import annotations

import argparse
import glob
import shutil
import stat
import subprocess
import sys
import tempfile
from pathlib import Path

INKSCAPE_SHIM_CODE = '''#!/usr/bin/env python3
"""Lightweight headless `inkscape` CLI shim for MyST Markdown SVG->PDF/PNG conversion.

Supports Inkscape 1.x and 0.92 CLI flags used by MyST (`mystmd`) and build scripts:
  inkscape input.svg --export-area-drawing --export-type=pdf --export-filename=output.pdf
  inkscape input.svg --export-filename=output.pdf
  inkscape input.svg --export-pdf=output.pdf
  inkscape input.svg --export-png=output.png
  inkscape input.svg -o output.pdf
"""

from __future__ import annotations

import ctypes
import os
import shutil
import subprocess
import sys
from pathlib import Path


def _find_rsvg_convert() -> str | None:
    for candidate in (
        shutil.which("rsvg-convert"),
        str(Path.home() / ".local" / "bin" / "rsvg-convert"),
        "/usr/bin/rsvg-convert",
        "/usr/local/bin/rsvg-convert",
    ):
        if candidate and Path(candidate).is_file() and os.access(candidate, os.X_OK):
            return candidate
    return None


def _ctypes_rsvg_to_pdf(svg_path: Path, out_path: Path) -> None:
    """Fallback SVG->PDF conversion using system librsvg-2.so.2 + libcairo.so.2 via ctypes."""
    rsvg = ctypes.CDLL("librsvg-2.so.2")
    cairo = ctypes.CDLL("libcairo.so.2")

    class RsvgDimensionData(ctypes.Structure):
        _fields_ = [
            ("width", ctypes.c_int),
            ("height", ctypes.c_int),
            ("em", ctypes.c_double),
            ("ex", ctypes.c_double),
        ]

    err = ctypes.c_void_p(None)
    rsvg.rsvg_handle_new_from_file.argtypes = [ctypes.c_char_p, ctypes.POINTER(ctypes.c_void_p)]
    rsvg.rsvg_handle_new_from_file.restype = ctypes.c_void_p
    handle = rsvg.rsvg_handle_new_from_file(str(svg_path).encode("utf-8"), ctypes.byref(err))
    if not handle:
        raise RuntimeError(f"librsvg failed to load {svg_path}")

    dim = RsvgDimensionData()
    rsvg.rsvg_handle_get_dimensions.argtypes = [ctypes.c_void_p, ctypes.POINTER(RsvgDimensionData)]
    rsvg.rsvg_handle_get_dimensions(handle, ctypes.byref(dim))
    width = float(dim.width if dim.width > 0 else 600)
    height = float(dim.height if dim.height > 0 else 400)

    cairo.cairo_pdf_surface_create.argtypes = [ctypes.c_char_p, ctypes.c_double, ctypes.c_double]
    cairo.cairo_pdf_surface_create.restype = ctypes.c_void_p
    surface = cairo.cairo_pdf_surface_create(str(out_path).encode("utf-8"), width, height)

    cairo.cairo_create.argtypes = [ctypes.c_void_p]
    cairo.cairo_create.restype = ctypes.c_void_p
    cr = cairo.cairo_create(surface)

    rsvg.rsvg_handle_render_cairo.argtypes = [ctypes.c_void_p, ctypes.c_void_p]
    rsvg.rsvg_handle_render_cairo.restype = ctypes.c_int
    ok = rsvg.rsvg_handle_render_cairo(handle, cr)

    cairo.cairo_surface_flush.argtypes = [ctypes.c_void_p]
    cairo.cairo_surface_flush(surface)
    cairo.cairo_destroy.argtypes = [ctypes.c_void_p]
    cairo.cairo_destroy(cr)
    cairo.cairo_surface_finish.argtypes = [ctypes.c_void_p]
    cairo.cairo_surface_finish(surface)
    cairo.cairo_surface_destroy.argtypes = [ctypes.c_void_p]
    cairo.cairo_surface_destroy(surface)
    if not ok:
        raise RuntimeError(f"librsvg failed to render {svg_path} to {out_path}")


def main(argv: list[str]) -> int:
    if "--version" in argv or "-V" in argv:
        print("Inkscape 1.2.2 (RAE headless rsvg-convert shim)")
        return 0

    input_svg: str | None = None
    output_file: str | None = None
    export_type: str | None = None
    dpi: str | None = None

    i = 0
    while i < len(argv):
        arg = argv[i]
        if arg.startswith("--export-filename="):
            output_file = arg.split("=", 1)[1]
        elif arg in ("--export-filename", "-o") and i + 1 < len(argv):
            output_file = argv[i + 1]
            i += 1
        elif arg.startswith("--export-pdf="):
            output_file = arg.split("=", 1)[1]
            export_type = "pdf"
        elif arg.startswith("--export-png="):
            output_file = arg.split("=", 1)[1]
            export_type = "png"
        elif arg.startswith("--export-type="):
            export_type = arg.split("=", 1)[1].lstrip(".").lower()
        elif arg == "--export-type" and i + 1 < len(argv):
            export_type = argv[i + 1].lstrip(".").lower()
            i += 1
        elif arg.startswith("--export-dpi="):
            dpi = arg.split("=", 1)[1]
        elif arg in ("--export-dpi", "-d") and i + 1 < len(argv):
            dpi = argv[i + 1]
            i += 1
        elif not arg.startswith("-") and input_svg is None:
            input_svg = arg
        i += 1

    if input_svg is None:
        print("inkscape shim error: no input SVG file specified", file=sys.stderr)
        return 1

    in_path = Path(input_svg)
    if output_file is None:
        ext = export_type or "pdf"
        out_path = in_path.with_suffix(f".{ext}")
    else:
        out_path = Path(output_file)

    fmt = (export_type or out_path.suffix.lstrip(".") or "pdf").lower()
    out_path.parent.mkdir(parents=True, exist_ok=True)

    rsvg_bin = _find_rsvg_convert()
    if rsvg_bin is not None:
        cmd = [rsvg_bin, "-f", fmt, "-o", str(out_path)]
        if dpi is not None:
            cmd.extend(["-d", dpi, "-p", dpi])
        cmd.append(str(in_path))
        res = subprocess.run(cmd, check=False)
        return res.returncode

    if fmt == "pdf":
        _ctypes_rsvg_to_pdf(in_path, out_path)
        return 0

    print(f"inkscape shim error: rsvg-convert not found for format {fmt}", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
'''


def sync_matplotlib_stix_fonts() -> None:
    """Copy Matplotlib's bundled STIX & DejaVu TrueType fonts into ~/.local/share/fonts/matplotlib."""
    try:
        import matplotlib
    except ImportError:
        return

    ttf_dir = Path(matplotlib.get_data_path()) / "fonts" / "ttf"
    if not ttf_dir.is_dir():
        return

    dest_dir = Path.home() / ".local" / "share" / "fonts" / "matplotlib"
    dest_dir.mkdir(parents=True, exist_ok=True)

    copied = 0
    for src_str in glob.glob(str(ttf_dir / "*.ttf")):
        src = Path(src_str)
        dst = dest_dir / src.name
        if not dst.exists():
            shutil.copy2(src, dst)
            copied += 1

    if copied > 0 and shutil.which("fc-cache"):
        subprocess.run(["fc-cache", "-f", str(dest_dir)], check=False)


def ensure_rsvg_convert(local_bin: Path) -> None:
    """Ensure rsvg-convert is available on PATH or in ~/.local/bin/rsvg-convert."""
    if shutil.which("rsvg-convert") or (local_bin / "rsvg-convert").is_file():
        return

    if not shutil.which("apt-get") or not shutil.which("dpkg-deb"):
        return

    with tempfile.TemporaryDirectory(prefix="rsvg_pkg_") as tmpdir:
        res = subprocess.run(
            ["apt-get", "download", "librsvg2-bin"],
            cwd=tmpdir,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=False,
        )
        if res.returncode != 0:
            return
        debs = list(Path(tmpdir).glob("librsvg2-bin_*.deb"))
        if not debs:
            return
        extract_dir = Path(tmpdir) / "extracted"
        subprocess.run(["dpkg-deb", "-x", str(debs[0]), str(extract_dir)], check=False)
        candidate = extract_dir / "usr" / "bin" / "rsvg-convert"
        if candidate.is_file():
            local_bin.mkdir(parents=True, exist_ok=True)
            target = local_bin / "rsvg-convert"
            shutil.copy2(candidate, target)
            target.chmod(target.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)


def ensure_inkscape() -> Path:
    """Ensure an `inkscape` CLI binary or shim is available for MyST SVG->PDF conversion."""
    sync_matplotlib_stix_fonts()
    local_bin = Path.home() / ".local" / "bin"
    local_bin.mkdir(parents=True, exist_ok=True)
    ensure_rsvg_convert(local_bin)

    existing = shutil.which("inkscape")
    if existing:
        return Path(existing)

    shim_path = local_bin / "inkscape"
    shim_path.write_text(INKSCAPE_SHIM_CODE, encoding="utf-8")
    shim_path.chmod(shim_path.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
    return shim_path


def check_pdf_fonts(pdf_path: Path, verbose: bool = False) -> bool:
    """Run `pdffonts` on `pdf_path` and fail if any Type 3 or unembedded font is present."""
    if not pdf_path.is_file():
        print(f"ERROR: PDF file not found: {pdf_path}", file=sys.stderr)
        return False

    pdffonts_bin = shutil.which("pdffonts")
    if not pdffonts_bin:
        print("ERROR: `pdffonts` (poppler-utils) is not installed on PATH.", file=sys.stderr)
        return False

    proc = subprocess.run([pdffonts_bin, str(pdf_path)], capture_output=True, text=True, check=True)
    lines = [line for line in proc.stdout.splitlines() if line.strip()]
    if len(lines) <= 2:
        print(f"WARNING: No fonts reported by pdffonts in {pdf_path}")
        return True

    data_lines = lines[2:]
    type3_fonts: list[str] = []
    unembedded_fonts: list[str] = []

    for line in data_lines:
        # pdffonts fixed columns: name, type, encoding, emb, sub, uni, object ID
        tokens = line.split()
        if len(tokens) < 6:
            continue
        # Last 5 tokens are: emb, sub, uni, obj_num, obj_gen
        emb = tokens[-5]
        font_name = tokens[0]
        if "Type 3" in line:
            type3_fonts.append(line)
        if emb.lower() != "yes":
            unembedded_fonts.append(f"{font_name} (emb={emb}): {line}")

    if verbose or type3_fonts or unembedded_fonts:
        print(f"=== pdffonts report for {pdf_path} ===")
        print(proc.stdout.rstrip())

    if type3_fonts:
        print(
            f"\nERROR: {pdf_path} contains {len(type3_fonts)} IEEE-prohibited Type 3 bitmap font(s)!\n"
            "Fix: Set `pdf.fonttype = 42`, `ps.fonttype = 42`, `mathtext.fontset = 'stix'`, "
            "and `text.usetex = False` in Matplotlib rcParams.",
            file=sys.stderr,
        )
        return False

    if unembedded_fonts:
        print(
            f"\nERROR: {pdf_path} contains {len(unembedded_fonts)} unembedded font(s) (emb != yes):\n  "
            + "\n  ".join(unembedded_fonts),
            file=sys.stderr,
        )
        return False

    print(
        f"Font audit passed for {pdf_path.name}: {len(data_lines)} font(s), "
        "0 Type 3 bitmap fonts, 100% embedded (IEEE PDF eXpress compliant)."
    )
    return True


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Ensure Inkscape SVG->PDF support and verify zero Type 3 / unembedded PDF fonts."
    )
    parser.add_argument(
        "--ensure-inkscape",
        action="store_true",
        help="Ensure inkscape (or rsvg-convert shim) and Matplotlib STIX fonts are installed.",
    )
    parser.add_argument(
        "--check-pdf",
        nargs="+",
        type=Path,
        default=[],
        help="One or more compiled PDF paths to audit with pdffonts.",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Always print the full pdffonts table.",
    )
    args = parser.parse_args()

    if args.ensure_inkscape or not args.check_pdf:
        inkscape_path = ensure_inkscape()
        if args.verbose:
            print(f"Inkscape CLI ready at: {inkscape_path}")

    all_ok = True
    for pdf in args.check_pdf:
        if not check_pdf_fonts(pdf, verbose=args.verbose):
            all_ok = False

    return 0 if all_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
