#!/usr/bin/env python3
"""Generate a publication-style inline text-diff PDF between two manuscript versions or Git commits.

Supports comparing:
1. Any two Git commit refs, tags, or branches (e.g., ``jner-submission-2025`` vs ``HEAD`` or ``WORKTREE``),
   with automatic fallback to ``versions/jner_submission_2025.md`` or working-tree files when ``.git/objects``
   contains unhydrated OneDrive cloud-only stubs.
2. Any two Markdown file paths directly (or a Git ref against a file path / working tree).
3. Reconstructed historical snapshots from ``_build/site/myst.search.json`` (e.g., ``rev1`` or
   ``myst-search:/causal-framework-precision-rehab-2``).
"""

from __future__ import annotations

import argparse
import difflib
import itertools
import json
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Literal
from xml.sax.saxutils import escape as xml_escape

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.pdfgen import canvas
from reportlab.platypus import HRFlowable, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

DEFAULT_MANUSCRIPT_FILE = "Causal Framework for Precision Rehab.md"
JNER_2025_TAG = "jner-submission-2025"
JNER_2025_COMMIT = "a2ba24491dcf0f6c4fe4593c90cb4cfad95b9c6e"
JNER_2025_FALLBACK_RELPATH = Path("versions") / "jner_submission_2025.md"
MYST_SEARCH_RELPATH = Path("_build") / "site" / "myst.search.json"

WORKTREE_ALIASES = frozenset({"WORKTREE", "WORKING", "WORKSPACE", "CURRENT", "."})
HEAD_ALIASES = frozenset({"HEAD", "main", "master", "origin/main"})

TOKEN_PATTERN = re.compile(
    r"\{[a-zA-Z0-9_:-]+\}`[^`]+`"
    r"|[\"'`“‘*]*[A-Za-z0-9_]+(?:[-'’][A-Za-z0-9_]+)*[\"'’”*]*"
    r"|[^\w\s]+"
)
WORD_LIKE_PATTERN = re.compile(r"[A-Za-z0-9]")
NO_SPACE_BEFORE = frozenset({".", ",", ";", ":", "!", "?", ")", "]", "}", "”", "’", "%"})
NO_SPACE_AFTER = frozenset({"(", "[", "{", "“", "‘"})

TARGET_LABEL_PATTERN = re.compile(r"^\([A-Za-z0-9_:-]+\)=\s*$")
HEADING_PATTERN = re.compile(r"^(#{1,6})\s+(.*\S)\s*$")
LIST_ITEM_PATTERN = re.compile(r"^(\s*(?:[-*+]|\d+[.)]))\s+(.*\S)\s*$")
ABSTRACT_MARKER_PATTERN = re.compile(r'^\+{3}\s*\{.*"part"\s*:\s*"abstract".*\}\s*$')
BLOCK_BREAK_PATTERN = re.compile(r"^\+{3}(?:\s*\{.*\})?\s*$")

SIMILARITY_PAIR_THRESHOLD = 0.25

BlockType = Literal["title", "heading", "paragraph", "list_item", "comment"]
DiffTag = Literal["equal", "insert", "delete"]
BlockStatus = Literal["unchanged", "modified", "added", "removed"]


@dataclass(frozen=True)
class ManuscriptBlock:
    """A logical text block extracted from a MyST Markdown manuscript."""

    block_type: BlockType
    level: int
    text: str


@dataclass(frozen=True)
class DiffSpan:
    """An inline word/token diff span within a manuscript block."""

    tag: DiffTag
    text: str
    word_count: int


@dataclass(frozen=True)
class BlockDiff:
    """Diff result for a single manuscript block (heading, paragraph, list item, or comment)."""

    block_type: BlockType
    level: int
    status: BlockStatus
    spans: list[DiffSpan]
    words_added: int
    words_removed: int
    words_unchanged: int


@dataclass(frozen=True)
class DocumentDiff:
    """Complete block- and word-level diff between two manuscript versions."""

    source_a_label: str
    source_b_label: str
    blocks: list[BlockDiff]
    words_added: int
    words_removed: int
    words_unchanged: int
    blocks_added: int
    blocks_removed: int
    blocks_modified: int
    blocks_unchanged: int


def _default_repo_dir() -> Path:
    return Path(__file__).resolve().parent.parent


def _try_read_text(path: Path) -> str | None:
    """Read UTF-8 text from ``path``, returning ``None`` if missing or an unhydrated cloud stub."""
    try:
        if path.is_file():
            return path.read_text(encoding="utf-8")
    except OSError:
        return None
    return None


def _is_jner_2025_ref(source_str: str, repo_dir: Path) -> bool:
    """Return True if ``source_str`` refers to the JNER 2025 submission tag or commit."""
    normalized = source_str.strip()
    if normalized == JNER_2025_TAG:
        return True
    if len(normalized) >= 7 and JNER_2025_COMMIT.startswith(normalized.lower()):
        return True
    tag_file = repo_dir / ".git" / "refs" / "tags" / normalized
    tag_sha = _try_read_text(tag_file)
    return bool(tag_sha is not None and tag_sha.strip() == JNER_2025_COMMIT)


def reconstruct_from_myst_search(
    search_json_path: str | Path,
    slug: str = "/causal-framework-precision-rehab-2",
) -> str:
    """Reconstruct a Markdown document from a MyST ``myst.search.json`` index."""
    path = Path(search_json_path)
    raw = _try_read_text(path)
    if raw is None:
        raise FileNotFoundError(f"Cannot read MyST search index at {path}")

    data = json.loads(raw)
    normalized_slug = slug if slug.startswith("/") else f"/{slug}"
    records = [r for r in data.get("records", []) if str(r.get("url", "")).split("#")[0] == normalized_slug]
    if not records:
        available = sorted({str(r.get("url", "")).split("#")[0] for r in data.get("records", [])})
        raise ValueError(f"Slug {normalized_slug!r} not found in {path}. Available slugs: {available}")

    lines: list[str] = []
    seen_abstract_body = False
    for rec in records:
        rec_type = str(rec.get("type", ""))
        hierarchy = rec.get("hierarchy", {})
        if rec_type.startswith("lvl"):
            level_num = int(rec_type.replace("lvl", ""))
            heading_text = str(hierarchy.get(rec_type, "")).strip()
            if heading_text:
                if level_num == 1:
                    lines.append(f"---\ntitle: {heading_text}\n---\n")
                else:
                    hashes = "#" * level_num
                    lines.append(f"{hashes} {heading_text}\n")
        elif rec_type == "content":
            content = str(rec.get("content", ""))
            # Clean compiled LaTeX / MyST search artifacts (figure captions, @endfloat footer, etc.)
            cleaned_paras: list[str] = []
            for para in content.split("\n\n"):
                stripped = para.strip()
                if not stripped:
                    continue
                if stripped.startswith(("[]%", "@endfloat")):
                    continue
                if re.match(r"^Figure[\s\xa0]+\d+\s*:", stripped):
                    continue
                stripped = re.sub(r"\s*DON'T EDIT\..*$", "", stripped, flags=re.DOTALL).strip()
                if stripped:
                    cleaned_paras.append(stripped)
            if cleaned_paras:
                if not seen_abstract_body and set(hierarchy.keys()) == {"lvl1"}:
                    lines.append('+++ {"part": "abstract"}')
                    lines.extend(cleaned_paras)
                    lines.append("+++\n")
                    seen_abstract_body = True
                else:
                    lines.extend(cleaned_paras)
                    lines.append("")

    return "\n\n".join(lines).strip() + "\n"


def resolve_manuscript_source(
    source: str | Path,
    file_path: str = DEFAULT_MANUSCRIPT_FILE,
    repo_dir: str | Path | None = None,
) -> tuple[str, str]:
    """Resolve a manuscript source specification (file path, working tree keyword, or Git ref).

    Returns:
        Tuple of ``(markdown_text, human_readable_source_label)``.
    """
    resolved_repo = Path(repo_dir).resolve() if repo_dir is not None else _default_repo_dir()
    source_str = str(source).strip()

    # 1. Explicit working-tree alias
    if source_str.upper() in WORKTREE_ALIASES:
        wt_path = resolved_repo / file_path
        wt_text = _try_read_text(wt_path)
        if wt_text is None:
            raise FileNotFoundError(f"Working-tree manuscript not found or unreadable: {wt_path}")
        return wt_text, f"WORKTREE ({file_path})"

    # 2. Direct file path (absolute or relative to current directory or repo_dir)
    if not isinstance(source, Path) and source_str.startswith("myst-search:"):
        slug = source_str.split("myst-search:", 1)[1].strip() or "/causal-framework-precision-rehab-2"
        search_path = resolved_repo / MYST_SEARCH_RELPATH
        return (
            reconstruct_from_myst_search(search_path, slug=slug),
            f"myst.search.json ({slug})",
        )

    candidate_paths = [Path(source)]
    if not Path(source).is_absolute():
        candidate_paths.append(resolved_repo / source_str)

    for cand in candidate_paths:
        text = _try_read_text(cand)
        if text is not None:
            try:
                rel = cand.resolve().relative_to(resolved_repo)
                return text, str(rel)
            except ValueError:
                return text, str(cand)

    # 3. Try Git show `<source>:<file_path>` (or `<source>` directly if it already contains `:<path>`)
    git_spec = source_str if ":" in source_str else f"{source_str}:{file_path}"
    proc = subprocess.run(
        ["git", "-C", str(resolved_repo), "show", git_spec],
        check=False,
        capture_output=True,
        text=True,
    )
    if proc.returncode == 0:
        return proc.stdout, f"git:{git_spec}"

    # 4. Fallbacks when .git/objects or .git/refs are unhydrated OneDrive stubs (or SIGBUS / EIO)
    if _is_jner_2025_ref(source_str, resolved_repo):
        fallback_path = resolved_repo / JNER_2025_FALLBACK_RELPATH
        fallback_text = _try_read_text(fallback_path)
        if fallback_text is not None:
            return (
                fallback_text,
                f"{source_str} (fallback: {JNER_2025_FALLBACK_RELPATH.as_posix()})",
            )

    if source_str in HEAD_ALIASES:
        wt_path = resolved_repo / file_path
        wt_text = _try_read_text(wt_path)
        if wt_text is not None:
            return wt_text, f"{source_str} (fallback: working tree {file_path})"

    if source_str in {"rev1", "versions/rev1.md", "rev1.md"}:
        search_path = resolved_repo / MYST_SEARCH_RELPATH
        if _try_read_text(search_path) is not None:
            return (
                reconstruct_from_myst_search(search_path, slug="/causal-framework-precision-rehab-2"),
                "versions/rev1.md (reconstructed from _build/site/myst.search.json)",
            )

    stderr_detail = proc.stderr.strip() or f"git exited with return code {proc.returncode}"
    raise RuntimeError(
        f"Could not resolve source {source_str!r} as a readable file or Git ref ({git_spec}): {stderr_detail}"
    )


def strip_myst_figures_and_comments(text: str, include_comments: bool = False) -> str:
    """Strip MyST figure directives and (unless ``include_comments=True``) comments from Markdown."""
    # Remove HTML comments <!-- ... --> when comments are excluded
    if not include_comments:
        text = re.sub(r"<!--.*?-->", "", text, flags=re.DOTALL)

    lines = text.splitlines()
    out_lines: list[str] = []
    in_figure = False
    figure_fence_closer: str | None = None

    for line in lines:
        stripped = line.strip()
        # Handle commented-out lines early when include_comments is False
        if not include_comments and stripped.startswith("%"):
            continue

        # Detect start of figure directive: ```{figure}, :::{figure}, or "`{figure}
        uncommented = stripped.lstrip("%").strip()
        if not in_figure:
            fig_match = re.match(r'^(`{3,}|:{3,}|"`)\{figure\}(?:\s|$)', uncommented)
            if fig_match is not None:
                in_figure = True
                opener = fig_match.group(1)
                figure_fence_closer = '"`' if opener == '"`' else opener
                continue
        else:
            if figure_fence_closer is not None and (
                uncommented == figure_fence_closer or uncommented.startswith(figure_fence_closer)
            ):
                in_figure = False
                figure_fence_closer = None
            continue

        out_lines.append(line)

    return "\n".join(out_lines)


def parse_myst_blocks(text: str, include_comments: bool = False) -> list[ManuscriptBlock]:
    """Parse MyST Markdown text into ordered structural blocks (title, headings, paragraphs, list items)."""
    cleaned = strip_myst_figures_and_comments(text, include_comments=include_comments)
    lines = cleaned.splitlines()
    blocks: list[ManuscriptBlock] = []

    idx = 0
    n_lines = len(lines)

    # 1. Parse optional YAML frontmatter at top of file
    while idx < n_lines and not lines[idx].strip():
        idx += 1
    if idx < n_lines and lines[idx].strip() == "---":
        idx += 1
        title_value: str | None = None
        while idx < n_lines and lines[idx].strip() != "---":
            fm_line = lines[idx].strip()
            if fm_line.startswith("title:"):
                title_value = fm_line.split("title:", 1)[1].strip().strip("\"'")
            idx += 1
        if idx < n_lines and lines[idx].strip() == "---":
            idx += 1
        if title_value:
            blocks.append(ManuscriptBlock(block_type="title", level=1, text=title_value))

    paragraph_buffer: list[str] = []

    def flush_paragraph() -> None:
        if paragraph_buffer:
            joined = " ".join(part.strip() for part in paragraph_buffer if part.strip())
            joined = re.sub(r"\s+", " ", joined).strip()
            if joined:
                blocks.append(ManuscriptBlock(block_type="paragraph", level=0, text=joined))
            paragraph_buffer.clear()

    while idx < n_lines:
        raw_line = lines[idx]
        stripped = raw_line.strip()
        idx += 1

        if not stripped:
            flush_paragraph()
            continue

        # Target anchors like `(odtr)=`
        if TARGET_LABEL_PATTERN.match(stripped):
            flush_paragraph()
            continue

        # Abstract / block break markers `+++ {"part": "abstract"}` or `+++`
        if ABSTRACT_MARKER_PATTERN.match(stripped):
            flush_paragraph()
            blocks.append(ManuscriptBlock(block_type="heading", level=2, text="Abstract"))
            continue
        if BLOCK_BREAK_PATTERN.match(stripped):
            flush_paragraph()
            continue

        # Comment lines (only reached if include_comments=True)
        if stripped.startswith("%"):
            flush_paragraph()
            comment_body = stripped.lstrip("%").strip()
            if comment_body and not TARGET_LABEL_PATTERN.match(comment_body):
                blocks.append(ManuscriptBlock(block_type="comment", level=0, text=comment_body))
            continue

        # Markdown headings `#` .. `######`
        heading_match = HEADING_PATTERN.match(stripped)
        if heading_match is not None:
            flush_paragraph()
            level = len(heading_match.group(1))
            heading_text = re.sub(r"\s+", " ", heading_match.group(2)).strip()
            block_type: BlockType = "title" if level == 1 and not blocks else "heading"
            blocks.append(ManuscriptBlock(block_type=block_type, level=level, text=heading_text))
            continue

        # Bulleted or numbered list items
        list_match = LIST_ITEM_PATTERN.match(raw_line)
        if list_match is not None:
            flush_paragraph()
            marker = list_match.group(1).strip()
            item_body = re.sub(r"\s+", " ", list_match.group(2)).strip()
            blocks.append(ManuscriptBlock(block_type="list_item", level=0, text=f"{marker} {item_body}"))
            continue

        paragraph_buffer.append(stripped)

    flush_paragraph()
    return blocks


def tokenize_words(text: str) -> list[str]:
    """Tokenize manuscript prose into words, MyST citation/ref roles, and punctuation tokens."""
    return TOKEN_PATTERN.findall(text)


def _count_real_words(tokens: list[str]) -> int:
    """Count tokens containing alphanumeric characters (excluding standalone punctuation)."""
    return sum(1 for tok in tokens if WORD_LIKE_PATTERN.search(tok) is not None)


def _join_tokens(tokens: list[str]) -> str:
    """Join word and punctuation tokens into natural prose spacing."""
    if not tokens:
        return ""
    parts: list[str] = [tokens[0]]
    for prev_tok, tok in itertools.pairwise(tokens):
        if tok[0] in NO_SPACE_BEFORE or prev_tok[-1] in NO_SPACE_AFTER:
            parts.append(tok)
        else:
            parts.append(" " + tok)
    return "".join(parts)


def diff_block_tokens(text_a: str, text_b: str) -> list[DiffSpan]:
    """Compute an inline word/token-level diff between ``text_a`` and ``text_b``."""
    tokens_a = tokenize_words(text_a)
    tokens_b = tokenize_words(text_b)
    matcher = difflib.SequenceMatcher(None, tokens_a, tokens_b, autojunk=False)

    spans: list[DiffSpan] = []
    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag == "equal":
            sub = tokens_a[i1:i2]
            if sub:
                spans.append(DiffSpan(tag="equal", text=_join_tokens(sub), word_count=_count_real_words(sub)))
        elif tag == "delete":
            sub = tokens_a[i1:i2]
            if sub:
                spans.append(DiffSpan(tag="delete", text=_join_tokens(sub), word_count=_count_real_words(sub)))
        elif tag == "insert":
            sub = tokens_b[j1:j2]
            if sub:
                spans.append(DiffSpan(tag="insert", text=_join_tokens(sub), word_count=_count_real_words(sub)))
        elif tag == "replace":
            sub_a = tokens_a[i1:i2]
            sub_b = tokens_b[j1:j2]
            if sub_a:
                spans.append(DiffSpan(tag="delete", text=_join_tokens(sub_a), word_count=_count_real_words(sub_a)))
            if sub_b:
                spans.append(DiffSpan(tag="insert", text=_join_tokens(sub_b), word_count=_count_real_words(sub_b)))
    return spans


def _make_single_status_block(block: ManuscriptBlock, status: Literal["unchanged", "added", "removed"]) -> BlockDiff:
    tokens = tokenize_words(block.text)
    wc = _count_real_words(tokens)
    span_tag: DiffTag = "equal" if status == "unchanged" else ("insert" if status == "added" else "delete")
    span = DiffSpan(tag=span_tag, text=block.text, word_count=wc)
    return BlockDiff(
        block_type=block.block_type,
        level=block.level,
        status=status,
        spans=[span],
        words_added=wc if status == "added" else 0,
        words_removed=wc if status == "removed" else 0,
        words_unchanged=wc if status == "unchanged" else 0,
    )


def _make_modified_block(block_a: ManuscriptBlock, block_b: ManuscriptBlock) -> BlockDiff:
    spans = diff_block_tokens(block_a.text, block_b.text)
    w_add = sum(s.word_count for s in spans if s.tag == "insert")
    w_rem = sum(s.word_count for s in spans if s.tag == "delete")
    w_eq = sum(s.word_count for s in spans if s.tag == "equal")
    status: BlockStatus = "unchanged" if (w_add == 0 and w_rem == 0) else "modified"
    return BlockDiff(
        block_type=block_b.block_type,
        level=block_b.level,
        status=status,
        spans=spans,
        words_added=w_add,
        words_removed=w_rem,
        words_unchanged=w_eq,
    )


def _block_similarity(block_a: ManuscriptBlock, block_b: ManuscriptBlock) -> float:
    if block_a.block_type != block_b.block_type:
        return 0.0
    tokens_a = tokenize_words(block_a.text)
    tokens_b = tokenize_words(block_b.text)
    if not tokens_a and not tokens_b:
        return 1.0
    return difflib.SequenceMatcher(None, tokens_a, tokens_b, autojunk=False).ratio()


def _align_replaced_blocks(
    slice_a: list[ManuscriptBlock],
    slice_b: list[ManuscriptBlock],
) -> list[BlockDiff]:
    """Align blocks within a replaced chunk so edited paragraphs receive inline word diffs."""
    if (
        len(slice_a) == 1
        and len(slice_b) == 1
        and slice_a[0].block_type == slice_b[0].block_type
        and _block_similarity(slice_a[0], slice_b[0]) >= SIMILARITY_PAIR_THRESHOLD
    ):
        return [_make_modified_block(slice_a[0], slice_b[0])]

    results: list[BlockDiff] = []
    idx_a = 0
    idx_b = 0
    len_a = len(slice_a)
    len_b = len(slice_b)

    while idx_a < len_a and idx_b < len_b:
        best_pair: tuple[int, int, float] | None = None
        for ia in range(idx_a, len_a):
            for ib in range(idx_b, len_b):
                sim = _block_similarity(slice_a[ia], slice_b[ib])
                if sim >= SIMILARITY_PAIR_THRESHOLD and (best_pair is None or sim > best_pair[2]):
                    best_pair = (ia, ib, sim)

        if best_pair is None:
            break

        pair_ia, pair_ib, _ = best_pair
        for rem_i in range(idx_a, pair_ia):
            results.append(_make_single_status_block(slice_a[rem_i], "removed"))
        for add_j in range(idx_b, pair_ib):
            results.append(_make_single_status_block(slice_b[add_j], "added"))

        results.append(_make_modified_block(slice_a[pair_ia], slice_b[pair_ib]))
        idx_a = pair_ia + 1
        idx_b = pair_ib + 1

    for rem_i in range(idx_a, len_a):
        results.append(_make_single_status_block(slice_a[rem_i], "removed"))
    for add_j in range(idx_b, len_b):
        results.append(_make_single_status_block(slice_b[add_j], "added"))

    return results


def compute_document_diff(
    blocks_a: list[ManuscriptBlock],
    blocks_b: list[ManuscriptBlock],
    source_a_label: str = "Source A",
    source_b_label: str = "Source B",
) -> DocumentDiff:
    """Compute block-aligned and word-level diffs between two parsed manuscripts."""
    keys_a = [(b.block_type, b.level, b.text) for b in blocks_a]
    keys_b = [(b.block_type, b.level, b.text) for b in blocks_b]
    matcher = difflib.SequenceMatcher(None, keys_a, keys_b, autojunk=False)

    block_diffs: list[BlockDiff] = []
    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag == "equal":
            for b in blocks_b[j1:j2]:
                block_diffs.append(_make_single_status_block(b, "unchanged"))
        elif tag == "delete":
            for b in blocks_a[i1:i2]:
                block_diffs.append(_make_single_status_block(b, "removed"))
        elif tag == "insert":
            for b in blocks_b[j1:j2]:
                block_diffs.append(_make_single_status_block(b, "added"))
        elif tag == "replace":
            block_diffs.extend(_align_replaced_blocks(blocks_a[i1:i2], blocks_b[j1:j2]))

    words_added = sum(b.words_added for b in block_diffs)
    words_removed = sum(b.words_removed for b in block_diffs)
    words_unchanged = sum(b.words_unchanged for b in block_diffs)
    blocks_added = sum(1 for b in block_diffs if b.status == "added")
    blocks_removed = sum(1 for b in block_diffs if b.status == "removed")
    blocks_modified = sum(1 for b in block_diffs if b.status == "modified")
    blocks_unchanged = sum(1 for b in block_diffs if b.status == "unchanged")

    return DocumentDiff(
        source_a_label=source_a_label,
        source_b_label=source_b_label,
        blocks=block_diffs,
        words_added=words_added,
        words_removed=words_removed,
        words_unchanged=words_unchanged,
        blocks_added=blocks_added,
        blocks_removed=blocks_removed,
        blocks_modified=blocks_modified,
        blocks_unchanged=blocks_unchanged,
    )


def _spans_to_reportlab_xml(spans: list[DiffSpan]) -> str:
    """Render ``DiffSpan`` items to ReportLab Paragraph XML with green additions and red strikethrough removals."""
    rendered: list[str] = []
    for idx, span in enumerate(spans):
        if not span.text:
            continue
        if idx > 0:
            prev_text = spans[idx - 1].text
            first_char = span.text[0]
            last_char = prev_text[-1] if prev_text else ""
            if first_char not in NO_SPACE_BEFORE and last_char not in NO_SPACE_AFTER:
                rendered.append(" ")

        escaped = xml_escape(span.text)
        if span.tag == "equal":
            rendered.append(escaped)
        elif span.tag == "insert":
            rendered.append(f'<font color="#146c32" backColor="#e6f4ea"><u>{escaped}</u></font>')
        elif span.tag == "delete":
            rendered.append(f'<font color="#b02a37" backColor="#fce8e6"><strike>{escaped}</strike></font>')
    return "".join(rendered)


def _build_pdf_styles() -> dict[str, ParagraphStyle]:
    base = getSampleStyleSheet()
    return {
        "banner_title": ParagraphStyle(
            "BannerTitle",
            parent=base["Heading1"],
            fontName="Helvetica-Bold",
            fontSize=14,
            leading=18,
            textColor=colors.HexColor("#1f2937"),
            spaceAfter=4,
        ),
        "banner_meta": ParagraphStyle(
            "BannerMeta",
            parent=base["BodyText"],
            fontName="Helvetica",
            fontSize=8.5,
            leading=12,
            textColor=colors.HexColor("#374151"),
        ),
        "title": ParagraphStyle(
            "ManuscriptTitle",
            parent=base["Heading1"],
            fontName="Times-Bold",
            fontSize=17,
            leading=22,
            textColor=colors.HexColor("#111827"),
            spaceBefore=10,
            spaceAfter=10,
        ),
        "h1": ParagraphStyle(
            "ManuscriptH1",
            parent=base["Heading1"],
            fontName="Helvetica-Bold",
            fontSize=14,
            leading=18,
            textColor=colors.HexColor("#111827"),
            spaceBefore=14,
            spaceAfter=6,
        ),
        "h2": ParagraphStyle(
            "ManuscriptH2",
            parent=base["Heading2"],
            fontName="Helvetica-Bold",
            fontSize=12.5,
            leading=16,
            textColor=colors.HexColor("#1f2937"),
            spaceBefore=12,
            spaceAfter=5,
        ),
        "h3": ParagraphStyle(
            "ManuscriptH3",
            parent=base["Heading3"],
            fontName="Helvetica-Bold",
            fontSize=11,
            leading=14.5,
            textColor=colors.HexColor("#374151"),
            spaceBefore=9,
            spaceAfter=4,
        ),
        "h4": ParagraphStyle(
            "ManuscriptH4",
            parent=base["Heading4"],
            fontName="Helvetica-BoldOblique",
            fontSize=10.5,
            leading=14,
            textColor=colors.HexColor("#374151"),
            spaceBefore=7,
            spaceAfter=3,
        ),
        "paragraph": ParagraphStyle(
            "ManuscriptParagraph",
            parent=base["BodyText"],
            fontName="Times-Roman",
            fontSize=10.5,
            leading=14.5,
            textColor=colors.HexColor("#111827"),
            spaceBefore=2,
            spaceAfter=7,
        ),
        "list_item": ParagraphStyle(
            "ManuscriptListItem",
            parent=base["BodyText"],
            fontName="Times-Roman",
            fontSize=10.5,
            leading=14.5,
            leftIndent=16,
            textColor=colors.HexColor("#111827"),
            spaceBefore=1,
            spaceAfter=5,
        ),
        "comment": ParagraphStyle(
            "ManuscriptComment",
            parent=base["BodyText"],
            fontName="Times-Italic",
            fontSize=9.5,
            leading=13,
            leftIndent=12,
            textColor=colors.HexColor("#4b5563"),
            backColor=colors.HexColor("#f9fafb"),
            spaceBefore=2,
            spaceAfter=6,
        ),
    }


def _select_block_style(block: BlockDiff, styles: dict[str, ParagraphStyle]) -> ParagraphStyle:
    if block.block_type == "title":
        return styles["title"]
    if block.block_type == "heading":
        if block.level <= 1:
            return styles["h1"]
        if block.level == 2:
            return styles["h2"]
        if block.level == 3:
            return styles["h3"]
        return styles["h4"]
    if block.block_type == "list_item":
        return styles["list_item"]
    if block.block_type == "comment":
        return styles["comment"]
    return styles["paragraph"]


def render_diff_to_pdf(
    doc_diff: DocumentDiff,
    output_pdf_path: str | Path,
    include_comments: bool = False,
    only_changed: bool = False,
) -> Path:
    """Render a computed ``DocumentDiff`` to a formatted PDF file."""
    out_path = Path(output_pdf_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    styles = _build_pdf_styles()
    story: list[object] = []

    # Summary Header Box
    story.append(Paragraph("Manuscript Text Diff Report", styles["banner_title"]))
    meta_html = (
        f"<b>Baseline (A):</b> {xml_escape(doc_diff.source_a_label)}<br/>"
        f"<b>Comparison (B):</b> {xml_escape(doc_diff.source_b_label)}<br/>"
        f"<b>Word Summary:</b> "
        f'<font color="#146c32"><b>+{doc_diff.words_added} added</b></font>, '
        f'<font color="#b02a37"><b>-{doc_diff.words_removed} removed</b></font>, '
        f"{doc_diff.words_unchanged} unchanged<br/>"
        f"<b>Block Summary:</b> {doc_diff.blocks_modified} modified, "
        f"{doc_diff.blocks_added} added, {doc_diff.blocks_removed} removed, "
        f"{doc_diff.blocks_unchanged} unchanged "
        f"(figures: stripped, comments: {'included' if include_comments else 'stripped'})<br/>"
        f"<b>Legend:</b> "
        f'<font color="#146c32" backColor="#e6f4ea"><u>Added text</u></font> &nbsp;&nbsp; '
        f'<font color="#b02a37" backColor="#fce8e6"><strike>Removed text</strike></font> &nbsp;&nbsp; '
        f"Unchanged text"
    )
    summary_table = Table(
        [[Paragraph(meta_html, styles["banner_meta"])]],
        colWidths=[7.0 * inch],
    )
    summary_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#f3f4f6")),
                ("BOX", (0, 0), (-1, -1), 0.75, colors.HexColor("#d1d5db")),
                ("LEFTPADDING", (0, 0), (-1, -1), 10),
                ("RIGHTPADDING", (0, 0), (-1, -1), 10),
                ("TOPPADDING", (0, 0), (-1, -1), 8),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
            ]
        )
    )
    story.append(summary_table)
    story.append(Spacer(1, 10))
    story.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor("#d1d5db")))
    story.append(Spacer(1, 8))

    rendered_count = 0
    for block in doc_diff.blocks:
        if only_changed and block.status == "unchanged" and block.block_type not in {"title", "heading"}:
            continue
        xml_body = _spans_to_reportlab_xml(block.spans)
        if not xml_body.strip():
            continue
        if block.block_type == "comment":
            xml_body = f"<b>[Comment]</b> {xml_body}"
        story.append(Paragraph(xml_body, _select_block_style(block, styles)))
        rendered_count += 1

    if rendered_count == 0:
        story.append(Paragraph("<i>No text differences found between the selected versions.</i>", styles["paragraph"]))

    def _draw_footer(canv: canvas.Canvas, doc: SimpleDocTemplate) -> None:
        canv.saveState()
        canv.setFont("Helvetica", 8)
        canv.setFillColor(colors.HexColor("#6b7280"))
        footer_left = f"{doc_diff.source_a_label}  ->  {doc_diff.source_b_label}"
        if len(footer_left) > 95:
            footer_left = footer_left[:92] + "..."
        canv.drawString(0.75 * inch, 0.45 * inch, footer_left)
        canv.drawRightString(letter[0] - 0.75 * inch, 0.45 * inch, f"Page {doc.page}")
        canv.restoreState()

    pdf_doc = SimpleDocTemplate(
        str(out_path),
        pagesize=letter,
        leftMargin=0.75 * inch,
        rightMargin=0.75 * inch,
        topMargin=0.75 * inch,
        bottomMargin=0.75 * inch,
        title=f"Manuscript Diff: {doc_diff.source_a_label} vs {doc_diff.source_b_label}",
    )
    pdf_doc.build(story, onFirstPage=_draw_footer, onLaterPages=_draw_footer)
    return out_path


def generate_diff_pdf(
    source_a: str | Path,
    source_b: str | Path,
    output_pdf_path: str | Path,
    file_path: str = DEFAULT_MANUSCRIPT_FILE,
    include_comments: bool = False,
    repo_dir: str | Path | None = None,
    only_changed: bool = False,
) -> Path:
    """Generate a PDF highlighting inline word additions and removals between two commits or files.

    Args:
        source_a: Baseline Git ref/commit/tag (e.g. ``"jner-submission-2025"``), file path,
            or ``"rev1"`` / ``"myst-search:<slug>"``.
        source_b: Comparison Git ref/commit/tag (e.g. ``"HEAD"`` or ``"WORKTREE"``) or file path.
        output_pdf_path: Destination path for the rendered PDF.
        file_path: Manuscript path within the repository when resolving Git refs or ``WORKTREE``.
        include_comments: Whether to include ``%`` comment lines in the comparison.
        repo_dir: Optional repository root directory (defaults to ``2023 - PrecisionRehab``).
        only_changed: If True, omit unchanged body paragraphs while preserving section headings.

    Returns:
        Resolved ``Path`` to the generated PDF file.
    """
    text_a, label_a = resolve_manuscript_source(source_a, file_path=file_path, repo_dir=repo_dir)
    text_b, label_b = resolve_manuscript_source(source_b, file_path=file_path, repo_dir=repo_dir)

    blocks_a = parse_myst_blocks(text_a, include_comments=include_comments)
    blocks_b = parse_myst_blocks(text_b, include_comments=include_comments)

    doc_diff = compute_document_diff(blocks_a, blocks_b, source_a_label=label_a, source_b_label=label_b)
    return render_diff_to_pdf(
        doc_diff,
        output_pdf_path=output_pdf_path,
        include_comments=include_comments,
        only_changed=only_changed,
    )


def build_arg_parser() -> argparse.ArgumentParser:
    """Create the CLI argument parser."""
    parser = argparse.ArgumentParser(
        description="Generate an inline word-diff PDF between two Git commits or MyST Markdown files."
    )
    parser.add_argument(
        "source_a",
        nargs="?",
        default=JNER_2025_TAG,
        help="Baseline Git commit/tag/ref or Markdown file path (default: %(default)s).",
    )
    parser.add_argument(
        "source_b",
        nargs="?",
        default="WORKTREE",
        help="Comparison Git commit/tag/ref, WORKTREE, or Markdown file path (default: %(default)s).",
    )
    parser.add_argument(
        "output_pos",
        nargs="?",
        default=None,
        help="Optional positional output PDF file path (overrides -o/--output if provided).",
    )
    parser.add_argument(
        "-o",
        "--output",
        default="exports/manuscript_diff.pdf",
        help="Output PDF file path (default: %(default)s).",
    )
    parser.add_argument(
        "-f",
        "--file",
        dest="file_path",
        default=DEFAULT_MANUSCRIPT_FILE,
        help="Manuscript path relative to repository root for Git refs (default: %(default)s).",
    )
    parser.add_argument(
        "--include-comments",
        action="store_true",
        help="Include MyST '%%' comment lines and HTML comments in the diff.",
    )
    parser.add_argument(
        "--only-changed",
        action="store_true",
        help="Render only modified/added/removed paragraphs under their section headings.",
    )
    parser.add_argument(
        "--repo-dir",
        default=None,
        help="Optional path to the repository root directory.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    """CLI entry point."""
    parser = build_arg_parser()
    args = parser.parse_args(argv)

    text_a, label_a = resolve_manuscript_source(args.source_a, file_path=args.file_path, repo_dir=args.repo_dir)
    text_b, label_b = resolve_manuscript_source(args.source_b, file_path=args.file_path, repo_dir=args.repo_dir)
    blocks_a = parse_myst_blocks(text_a, include_comments=args.include_comments)
    blocks_b = parse_myst_blocks(text_b, include_comments=args.include_comments)
    doc_diff = compute_document_diff(blocks_a, blocks_b, source_a_label=label_a, source_b_label=label_b)

    output_target = args.output_pos if args.output_pos is not None else args.output
    out_path = render_diff_to_pdf(
        doc_diff,
        output_pdf_path=output_target,
        include_comments=args.include_comments,
        only_changed=args.only_changed,
    )
    print(f"Baseline (A):   {doc_diff.source_a_label}")
    print(f"Comparison (B): {doc_diff.source_b_label}")
    print(
        f"Words:          +{doc_diff.words_added} added, "
        f"-{doc_diff.words_removed} removed, {doc_diff.words_unchanged} unchanged"
    )
    print(
        f"Blocks:         {doc_diff.blocks_modified} modified, "
        f"{doc_diff.blocks_added} added, {doc_diff.blocks_removed} removed, "
        f"{doc_diff.blocks_unchanged} unchanged"
    )
    print(f"Generated PDF:  {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
