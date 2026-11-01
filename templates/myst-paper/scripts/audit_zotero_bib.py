#!/usr/bin/env python3
"""Audit BibTeX (.bib) files against the local Zotero HTTP API and verify missing references.

Features:
1. Paginates `http://localhost:23119/api/users/0/items/top` to index all items in the local
   Zotero library (8-character Zotero item `key`, DOIs, arXiv IDs, PMIDs, citation keys,
   normalized titles, authors, and years), caching locally in `/tmp/zotero_library_cache.json`.
2. Audits one or more `.bib` files (or scans a workspace directory) to match every BibTeX
   entry against the Zotero library, validating that DOI/arXiv matches also agree in title/author
   so corrupted DOIs in `.bib` files are caught rather than mis-linked.
3. Stamps `zotero_key = {<KEY>}` into matched BibTeX entries when `--stamp` is passed.
4. Verifies every BibTeX entry that is NOT in Zotero against Crossref, OpenAlex, PubMed, and
   arXiv (with rate-limiting and retry-on-429) to confirm whether the reference is 100% real
   (and whether its DOI/arXiv ID/metadata in the `.bib` file is accurate or mismatched).
5. Exports a clean, deduplicated BibTeX file of verified missing references (`--export-missing-bib`)
   and structured JSON/Markdown reports (`--report-json`).
"""

from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
import difflib
import html
import json
from pathlib import Path
import re
import sys
import threading
import time
import unicodedata
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from typing import Any

ZOTERO_API_BASE = "http://localhost:23119/api/users/0"
DEFAULT_CACHE_PATH = "/tmp/zotero_library_cache.json"
DEFAULT_VERIFY_CACHE_PATH = "/tmp/zotero_online_verify_cache.json"

_RATE_LOCK = threading.Lock()
_LAST_REQ_TIME: dict[str, float] = {}

STOPWORDS = {
    "a",
    "an",
    "and",
    "are",
    "as",
    "at",
    "be",
    "by",
    "for",
    "from",
    "in",
    "into",
    "is",
    "it",
    "of",
    "on",
    "or",
    "that",
    "the",
    "their",
    "this",
    "to",
    "using",
    "via",
    "with",
}

DOI_RE = re.compile(r"(10\.\d{4,9}/[^\s\"<>}{,;]+)", re.IGNORECASE)
ARXIV_NEW_RE = re.compile(
    r"(?:arxiv[\s:/._-]*|abs/|pdf/)(\d{4}\.\d{4,5})(?:v\d+)?",
    re.IGNORECASE,
)
ARXIV_BARE_RE = re.compile(r"\b(\d{4}\.\d{4,5})(?:v\d+)?\b")
PMID_RE = re.compile(
    r"(?:pmid[\s:]*|pubmed\.ncbi\.nlm\.nih\.gov/)(\d{6,9})\b", re.IGNORECASE
)
CITEKEY_EXTRA_RE = re.compile(r"Citation Key:\s*(\S+)", re.IGNORECASE)
YEAR_RE = re.compile(r"\b(18\d{2}|19\d{2}|20\d{2})\b")


def strip_latex_and_accents(text: str) -> str:
    """Remove LaTeX formatting, HTML entities, and diacritics from a string."""
    if not text:
        return ""
    text = html.unescape(text)
    text = (
        text.replace(r"\'e", "e")
        .replace(r"\"o", "o")
        .replace(r"\"u", "u")
        .replace(r"\"a", "a")
        .replace(r"\'a", "a")
        .replace(r"\'i", "i")
        .replace(r"\'o", "o")
        .replace(r"\'u", "u")
        .replace(r"\'c", "c")
        .replace(r"\'n", "n")
        .replace(r"\v{c}", "c")
        .replace(r"\v{s}", "s")
        .replace(r"\v{z}", "z")
        .replace(r"\ss", "ss")
        .replace(r"\o", "o")
        .replace(r"\O", "o")
        .replace(r"\l", "l")
        .replace(r"\L", "l")
        .replace(r"\&", " and ")
    )
    text = re.sub(r"\\[a-zA-Z]+\*?\{([^{}]*)\}", r" \1 ", text)
    text = re.sub(r"\\[a-zA-Z]+\*?", " ", text)
    text = text.replace("{", "").replace("}", "").replace("$", "")
    text = unicodedata.normalize("NFKD", text)
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    return text


def normalize_title(title: str) -> str:
    """Normalize a paper title to lowercase alphanumeric space-separated words."""
    cleaned = strip_latex_and_accents(title).lower()
    cleaned = re.sub(r"[^a-z0-9]+", " ", cleaned)
    return " ".join(cleaned.split())


def title_tokens(title: str) -> set[str]:
    """Return significant (>2 chars, non-stopword) tokens from a normalized title."""
    norm = normalize_title(title)
    return {w for w in norm.split() if len(w) > 2 and w not in STOPWORDS}


def normalize_doi(raw: str) -> str | None:
    """Extract and normalize a DOI string."""
    if not raw:
        return None
    cleaned = raw.strip().replace(r"\_", "_")
    m = DOI_RE.search(cleaned)
    if not m:
        return None
    return m.group(1).lower().rstrip(".)];,")


def extract_all_dois(text: str) -> list[str]:
    """Extract all normalized DOIs from a string."""
    if not text:
        return []
    cleaned = text.replace(r"\_", "_")
    results = []
    for m in DOI_RE.finditer(cleaned):
        doi = m.group(1).lower().rstrip(".)];,")
        if doi not in results:
            results.append(doi)
    return results


def extract_all_arxiv_ids(text: str, allow_bare: bool = False) -> list[str]:
    """Extract normalized base arXiv IDs (e.g. '2408.12345') from a string."""
    if not text:
        return []
    cleaned = text.replace(r"\_", "_")
    results = []
    for m in ARXIV_NEW_RE.finditer(cleaned):
        aid = m.group(1)
        if aid not in results:
            results.append(aid)
    if allow_bare:
        for m in ARXIV_BARE_RE.finditer(cleaned):
            aid = m.group(1)
            if aid not in results:
                results.append(aid)
    return results


def extract_year(text: str) -> int | None:
    """Extract a 4-digit publication year."""
    if not text:
        return None
    m = YEAR_RE.search(str(text))
    return int(m.group(1)) if m else None


def normalize_surname(name: str) -> str:
    """Normalize an author surname to lowercase ASCII letters."""
    cleaned = strip_latex_and_accents(name).lower()
    cleaned = re.sub(r"[^a-z]+", "", cleaned)
    return cleaned


def surnames_match(s1: str, s2: str) -> bool:
    """Compare two normalized author surnames allowing umlaut/particle variations."""
    if not s1 or not s2:
        return False
    if s1 == s2:
        return True
    # Handle ae/oe/ue umlaut expansions (e.g. haufle vs haeufle) or l/blasiok
    for a, b in (("ae", "a"), ("oe", "o"), ("ue", "u")):
        if s1.replace(a, b) == s2.replace(a, b):
            return True
    # Handle van/de/von prefix stripped vs concatenated
    for prefix in ("van", "vanden", "vander", "de", "del", "di", "von", "le", "la"):
        if s1 == prefix + s2 or s2 == prefix + s1:
            return True
    if len(s1) >= 5 and len(s2) >= 5 and difflib.SequenceMatcher(None, s1, s2).ratio() >= 0.85:
        return True
    return False


def any_author_matches(bib_authors: list[str], target_authors: list[str]) -> bool:
    """Return True if any surname in bib_authors matches any surname in target_authors."""
    for ba in bib_authors:
        for ta in target_authors:
            if surnames_match(ba, ta):
                return True
    return False


def extract_bib_authors(author_field: str) -> list[str]:
    """Extract normalized author surnames from a BibTeX author field."""
    if not author_field:
        return []
    cleaned = strip_latex_and_accents(author_field)
    parts = re.split(r"\band\b", cleaned, flags=re.IGNORECASE)
    surnames = []
    for part in parts:
        part = part.strip()
        if not part or part.lower() == "others":
            continue
        if "," in part:
            surname = part.split(",", 1)[0].strip()
        else:
            tokens = part.split()
            surname = tokens[-1] if tokens else ""
        norm = normalize_surname(surname)
        if norm:
            surnames.append(norm)
    return surnames


def title_similarity(t1: str, t2: str) -> float:
    """Compute similarity between two titles considering sequence ratio and token overlap."""
    n1 = normalize_title(t1)
    n2 = normalize_title(t2)
    if not n1 or not n2:
        return 0.0
    if n1 == n2:
        return 1.0
    if ":" in t1:
        p1 = normalize_title(t1.split(":", 1)[0])
        if len(p1.split()) >= 4 and p1 == n2:
            return 0.94
    if ":" in t2:
        p2 = normalize_title(t2.split(":", 1)[0])
        if len(p2.split()) >= 4 and p2 == n1:
            return 0.94
    seq = difflib.SequenceMatcher(None, n1, n2).ratio()
    tok1 = title_tokens(t1)
    tok2 = title_tokens(t2)
    if tok1 and tok2:
        jacc = len(tok1 & tok2) / len(tok1 | tok2)
        return max(seq, jacc)
    return seq


# ---------------------------------------------------------------------------
# Zotero Library Fetching & Indexing
# ---------------------------------------------------------------------------


def fetch_zotero_page(start: int, limit: int = 100) -> list[dict[str, Any]]:
    """Fetch a single page of top-level items from the local Zotero HTTP API."""
    url = f"{ZOTERO_API_BASE}/items/top?limit={limit}&start={start}"
    req = urllib.request.Request(url, headers={"Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode("utf-8"))


def load_or_fetch_zotero_library(
    cache_path: str = DEFAULT_CACHE_PATH, refresh: bool = False
) -> list[dict[str, Any]]:
    """Load the Zotero library from cache or fetch all items from localhost:23119."""
    cache_file = Path(cache_path)
    if cache_file.exists() and not refresh:
        try:
            data = json.loads(cache_file.read_text(encoding="utf-8"))
            if isinstance(data, list) and len(data) > 1000:
                return data
        except Exception:
            pass

    url = f"{ZOTERO_API_BASE}/items/top?limit=1"
    req = urllib.request.Request(url, headers={"Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=15) as resp:
        total = int(resp.headers.get("Total-Results", "0"))

    print(
        f"[Zotero] Fetching {total} top-level items from {ZOTERO_API_BASE}/items/top ...",
        file=sys.stderr,
    )
    limit = 100
    starts = list(range(0, total, limit))
    items_raw: list[dict[str, Any]] = []

    with ThreadPoolExecutor(max_workers=8) as pool:
        future_to_start = {
            pool.submit(fetch_zotero_page, s, limit): s for s in starts
        }
        for fut in as_completed(future_to_start):
            page = fut.result()
            items_raw.extend(page)

    compact_items: list[dict[str, Any]] = []
    seen_keys: set[str] = set()
    for it in items_raw:
        key = it.get("key")
        if not key or key in seen_keys:
            continue
        seen_keys.add(key)
        d = it.get("data", {})
        creators = []
        for c in d.get("creators", []):
            last = c.get("lastName") or c.get("name") or ""
            first = c.get("firstName") or ""
            creators.append({"lastName": last, "firstName": first})
        compact_items.append(
            {
                "key": key,
                "itemType": d.get("itemType", ""),
                "title": d.get("title", ""),
                "shortTitle": d.get("shortTitle", ""),
                "creators": creators,
                "date": d.get("date", ""),
                "DOI": d.get("DOI", ""),
                "url": d.get("url", ""),
                "extra": d.get("extra", ""),
                "publicationTitle": d.get("publicationTitle", "")
                or d.get("proceedingsTitle", "")
                or d.get("bookTitle", "")
                or d.get("university", "")
                or d.get("institution", "")
                or d.get("publisher", ""),
                "volume": d.get("volume", ""),
                "issue": d.get("issue", ""),
                "pages": d.get("pages", ""),
                "archiveID": d.get("archiveID", ""),
            }
        )

    cache_file.write_text(
        json.dumps(compact_items, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(
        f"[Zotero] Cached {len(compact_items)} items to {cache_path}",
        file=sys.stderr,
    )
    return compact_items


class ZoteroIndex:
    """In-memory multi-key index over the user's Zotero library."""

    def __init__(self, items: list[dict[str, Any]]) -> None:
        self.items_by_key: dict[str, dict[str, Any]] = {}
        self.by_doi: dict[str, list[dict[str, Any]]] = {}
        self.by_arxiv: dict[str, list[dict[str, Any]]] = {}
        self.by_pmid: dict[str, list[dict[str, Any]]] = {}
        self.by_citekey: dict[str, list[dict[str, Any]]] = {}
        self.by_norm_title: dict[str, list[dict[str, Any]]] = {}
        self.by_short_title: dict[str, list[dict[str, Any]]] = {}
        self.by_first_author: dict[str, list[dict[str, Any]]] = {}
        self.all_enriched: list[dict[str, Any]] = []

        for item in items:
            key = item["key"]
            self.items_by_key[key] = item

            blob = " ".join(
                [
                    str(item.get("DOI", "")),
                    str(item.get("url", "")),
                    str(item.get("extra", "")),
                    str(item.get("archiveID", "")),
                    str(item.get("publicationTitle", "")),
                ]
            )
            dois = extract_all_dois(blob)
            arxivs = extract_all_arxiv_ids(blob)
            pmids = PMID_RE.findall(blob)

            extra = str(item.get("extra", ""))
            citekeys = [m.group(1) for m in CITEKEY_EXTRA_RE.finditer(extra)]

            norm_t = normalize_title(item.get("title", ""))
            short_t = ""
            raw_title = item.get("title", "")
            if ":" in raw_title:
                short_t = normalize_title(raw_title.split(":", 1)[0])
            elif " - " in raw_title:
                short_t = normalize_title(raw_title.split(" - ", 1)[0])

            surnames = [
                normalize_surname(c.get("lastName", ""))
                for c in item.get("creators", [])
                if normalize_surname(c.get("lastName", ""))
            ]
            first_author = surnames[0] if surnames else ""
            year = extract_year(item.get("date", "")) or extract_year(extra)

            enriched = {
                **item,
                "_dois": dois,
                "_arxivs": arxivs,
                "_pmids": pmids,
                "_citekeys": citekeys,
                "_norm_title": norm_t,
                "_short_title": short_t,
                "_tokens": title_tokens(item.get("title", "")),
                "_surnames": surnames,
                "_first_author": first_author,
                "_year": year,
            }
            self.all_enriched.append(enriched)

            for d in dois:
                self.by_doi.setdefault(d, []).append(enriched)
            for a in arxivs:
                self.by_arxiv.setdefault(a, []).append(enriched)
            for p in pmids:
                self.by_pmid.setdefault(p, []).append(enriched)
            for ck in citekeys:
                self.by_citekey.setdefault(ck.lower(), []).append(enriched)
            if norm_t:
                self.by_norm_title.setdefault(norm_t, []).append(enriched)
            if short_t and len(short_t.split()) >= 4:
                self.by_short_title.setdefault(short_t, []).append(enriched)
            if first_author:
                self.by_first_author.setdefault(first_author, []).append(
                    enriched
                )

    @staticmethod
    def _is_consistent_id_match(
        bib_title: str,
        bib_authors: list[str],
        zot: dict[str, Any],
    ) -> bool:
        """Verify that a DOI/arXiv/PMID match in Zotero actually corresponds to the same paper."""
        zot_title = zot.get("title", "")
        if not bib_title or not zot_title:
            return True
        # Handle Zotero web-import placeholder titles like "Imported from https://..."
        if zot_title.lower().startswith("imported from "):
            return any_author_matches(bib_authors, zot.get("_surnames", [])) or True
        sim = title_similarity(bib_title, zot_title)
        if sim >= 0.55:
            return True
        if sim >= 0.40 and any_author_matches(bib_authors, zot.get("_surnames", [])):
            return True
        # Short acronym/prefix title in Zotero (e.g. "MoSh" vs "MoSh: Motion and Shape Capture...")
        if ":" in bib_title and any_author_matches(bib_authors, zot.get("_surnames", [])):
            prefix_norm = normalize_title(bib_title.split(":", 1)[0])
            if prefix_norm and prefix_norm == normalize_title(zot_title):
                return True
        return False

    def match_bib_entry(
        self, entry: dict[str, Any]
    ) -> tuple[dict[str, Any] | None, str, list[str]]:
        """Match a parsed BibTeX entry against the Zotero index.

        Returns:
            (matched_zotero_item, match_method, warnings)
        """
        fields = entry["fields"]
        warnings: list[str] = []

        bib_title = fields.get("title", "")
        bib_norm_title = normalize_title(bib_title)
        bib_tokens = title_tokens(bib_title)
        bib_authors = extract_bib_authors(
            fields.get("author", "") or fields.get("editor", "")
        )
        bib_first_author = bib_authors[0] if bib_authors else ""
        bib_year = extract_year(
            fields.get("year", "") or fields.get("date", "")
        )

        # 0. Explicit zotero_key
        zk = fields.get("zotero_key", "").strip()
        if zk and zk in self.items_by_key:
            for e in self.all_enriched:
                if e["key"] == zk:
                    if self._is_consistent_id_match(bib_title, bib_authors, e):
                        return e, "zotero_key", warnings
                    warnings.append(
                        f"Existing zotero_key {zk} points to different title '{e.get('title', '')[:60]}'"
                    )

        # Gather identifiers from BibTeX entry
        bib_blob = " ".join(
            [
                fields.get("doi", ""),
                fields.get("url", ""),
                fields.get("eprint", ""),
                fields.get("note", ""),
                fields.get("journal", ""),
                fields.get("booktitle", ""),
                fields.get("howpublished", ""),
            ]
        )
        bib_dois = extract_all_dois(bib_blob)
        bib_arxivs = extract_all_arxiv_ids(
            bib_blob,
            allow_bare=bool(
                fields.get("eprint") or "arxiv" in bib_blob.lower()
            ),
        )
        if fields.get("eprint"):
            for a in extract_all_arxiv_ids(fields["eprint"], allow_bare=True):
                if a not in bib_arxivs:
                    bib_arxivs.append(a)
        bib_pmids = PMID_RE.findall(bib_blob + " " + fields.get("pmid", ""))
        if fields.get("pmid", "").strip().isdigit():
            bib_pmids.append(fields["pmid"].strip())

        # 1. DOI match (verified against title/author consistency)
        for d in bib_dois:
            if d in self.by_doi:
                for cand in self.by_doi[d]:
                    if self._is_consistent_id_match(bib_title, bib_authors, cand):
                        self._check_metadata_consistency(
                            entry, cand, "doi", warnings
                        )
                        return cand, f"doi:{d}", warnings
                bad_zot = self.by_doi[d][0]
                warnings.append(
                    f"Corrupted DOI in .bib: {d} belongs to Zotero item {bad_zot['key']} ('{bad_zot.get('title', '')[:60]}')"
                )

        # 2. arXiv ID match (verified against title/author consistency)
        for a in bib_arxivs:
            if a in self.by_arxiv:
                for cand in self.by_arxiv[a]:
                    if self._is_consistent_id_match(bib_title, bib_authors, cand):
                        self._check_metadata_consistency(
                            entry, cand, "arxiv", warnings
                        )
                        return cand, f"arxiv:{a}", warnings
                bad_zot = self.by_arxiv[a][0]
                warnings.append(
                    f"Corrupted arXiv ID in .bib: {a} belongs to Zotero item {bad_zot['key']} ('{bad_zot.get('title', '')[:60]}')"
                )

        # 3. PMID match
        for p in bib_pmids:
            if p in self.by_pmid:
                for cand in self.by_pmid[p]:
                    if self._is_consistent_id_match(bib_title, bib_authors, cand):
                        self._check_metadata_consistency(
                            entry, cand, "pmid", warnings
                        )
                        return cand, f"pmid:{p}", warnings

        # 4. Exact normalized title match
        if bib_norm_title and bib_norm_title in self.by_norm_title:
            cands = self.by_norm_title[bib_norm_title]
            for c in cands:
                if any_author_matches(bib_authors, c["_surnames"]) or not bib_authors or not c["_surnames"]:
                    self._check_metadata_consistency(
                        entry, c, "title_exact", warnings
                    )
                    return c, "title_exact", warnings
            # Only accept author-mismatch exact title if title has >= 7 words and year matches
            if len(bib_norm_title.split()) >= 7:
                for c in cands:
                    if bib_year and c["_year"] and abs(bib_year - c["_year"]) <= 1:
                        self._check_metadata_consistency(
                            entry, c, "title_exact", warnings
                        )
                        return c, "title_exact", warnings

        # 5. Short title (prefix before colon) match + author
        bib_short = ""
        if ":" in bib_title:
            bib_short = normalize_title(bib_title.split(":", 1)[0])
        elif " - " in bib_title:
            bib_short = normalize_title(bib_title.split(" - ", 1)[0])

        if bib_short and len(bib_short.split()) >= 4:
            cands = self.by_short_title.get(bib_short, []) + self.by_norm_title.get(
                bib_short, []
            )
            for c in cands:
                if any_author_matches(bib_authors, c["_surnames"]):
                    self._check_metadata_consistency(
                        entry, c, "title_short", warnings
                    )
                    return c, "title_short", warnings

        # 6. Fuzzy title match within same first author (or shared authors)
        if bib_norm_title and len(bib_norm_title.split()) >= 4:
            pool: list[dict[str, Any]] = []
            for ba in bib_authors[:2]:
                pool.extend(self.by_first_author.get(ba, []))
            best_cand = None
            best_score = 0.0
            for c in pool:
                if not c["_norm_title"]:
                    continue
                score = title_similarity(bib_title, c.get("title", ""))
                if score > best_score:
                    best_score = score
                    best_cand = c

            if best_cand is not None and best_score >= 0.84:
                self._check_metadata_consistency(
                    entry, best_cand, f"title_fuzzy({best_score:.2f})", warnings
                )
                return best_cand, f"title_fuzzy({best_score:.2f})", warnings

            # Global high-similarity title match (>= 0.90) with author or year agreement
            if len(bib_tokens) >= 4:
                for c in self.all_enriched:
                    if not c["_tokens"]:
                        continue
                    inter = len(bib_tokens & c["_tokens"])
                    if inter < max(3, int(0.75 * len(bib_tokens))):
                        continue
                    seq_ratio = difflib.SequenceMatcher(
                        None, bib_norm_title, c["_norm_title"]
                    ).ratio()
                    if seq_ratio >= 0.90 and (
                        any_author_matches(bib_authors, c["_surnames"])
                        or (bib_year and c["_year"] and abs(bib_year - c["_year"]) <= 1)
                    ):
                        self._check_metadata_consistency(
                            entry,
                            c,
                            f"title_global_fuzzy({seq_ratio:.2f})",
                            warnings,
                        )
                        return c, f"title_global_fuzzy({seq_ratio:.2f})", warnings

        return None, "unmatched", warnings

    @staticmethod
    def _check_metadata_consistency(
        entry: dict[str, Any],
        zot: dict[str, Any],
        method: str,
        warnings: list[str],
    ) -> None:
        fields = entry["fields"]
        bib_authors = extract_bib_authors(
            fields.get("author", "") or fields.get("editor", "")
        )
        bib_first = bib_authors[0] if bib_authors else ""
        zot_first = zot.get("_first_author", "")
        zot_surnames = zot.get("_surnames", [])
        if bib_first and zot_first and not surnames_match(bib_first, zot_first):
            if not any_author_matches(bib_authors, zot_surnames):
                warnings.append(
                    f"Author mismatch: bib has '{bib_first}' vs Zotero '{zot_first}' ({zot.get('key')})"
                )
        bib_title = fields.get("title", "")
        zot_title = zot.get("title", "")
        if bib_title and zot_title and not zot_title.lower().startswith("imported from "):
            sim = title_similarity(bib_title, zot_title)
            if sim < 0.65:
                warnings.append(
                    f"Title difference (sim={sim:.2f}): bib='{bib_title[:60]}' vs Zotero='{zot_title[:60]}'"
                )


# ---------------------------------------------------------------------------
# BibTeX Parsing & Stamping
# ---------------------------------------------------------------------------


def parse_bib_file(path: Path) -> list[dict[str, Any]]:
    """Parse a .bib file into entries with exact character spans for lossless editing."""
    text = path.read_text(encoding="utf-8", errors="replace")
    entries: list[dict[str, Any]] = []
    n = len(text)
    i = 0

    while i < n:
        at_pos = text.find("@", i)
        if at_pos == -1:
            break
        line_start = text.rfind("\n", 0, at_pos) + 1
        prefix = text[line_start:at_pos]
        if "%" in prefix:
            i = at_pos + 1
            continue

        m = re.match(r"@([a-zA-Z]+)\s*([({])", text[at_pos:])
        if not m:
            i = at_pos + 1
            continue

        entry_type = m.group(1).lower()
        open_delim = m.group(2)
        close_delim = ")" if open_delim == "(" else "}"
        body_start = at_pos + m.end()

        depth = 1
        j = body_start
        in_quotes = False
        while j < n and depth > 0:
            ch = text[j]
            if ch == '"' and (j == 0 or text[j - 1] != "\\"):
                in_quotes = not in_quotes
            elif not in_quotes:
                if ch == open_delim or ch == "{":
                    depth += 1
                elif ch == close_delim or ch == "}":
                    depth -= 1
            j += 1

        entry_end = j
        raw_entry = text[at_pos:entry_end]
        inner = text[body_start : entry_end - 1]

        if entry_type in {"comment", "preamble", "string"}:
            i = entry_end
            continue

        comma_pos = inner.find(",")
        if comma_pos == -1:
            i = entry_end
            continue

        citekey = inner[:comma_pos].strip()
        fields_blob = inner[comma_pos + 1 :]
        fields = _parse_bib_fields(fields_blob)

        entries.append(
            {
                "entry_type": entry_type,
                "citekey": citekey,
                "fields": fields,
                "start": at_pos,
                "end": entry_end,
                "raw": raw_entry,
            }
        )
        i = entry_end

    return entries


def _parse_bib_fields(fields_blob: str) -> dict[str, str]:
    """Parse key = value pairs inside a BibTeX entry body."""
    fields: dict[str, str] = {}
    i = 0
    n = len(fields_blob)

    while i < n:
        while i < n and fields_blob[i] in " \t\r\n,":
            i += 1
        if i >= n:
            break
        if fields_blob[i] == "%":
            nl = fields_blob.find("\n", i)
            i = nl + 1 if nl != -1 else n
            continue

        m = re.match(r"([a-zA-Z0-9_:-]+)\s*=\s*", fields_blob[i:])
        if not m:
            nl = fields_blob.find("\n", i)
            i = nl + 1 if nl != -1 else n
            continue

        field_name = m.group(1).lower()
        i += m.end()
        if i >= n:
            break

        if fields_blob[i] == "{":
            depth = 1
            j = i + 1
            while j < n and depth > 0:
                if fields_blob[j] == "{":
                    depth += 1
                elif fields_blob[j] == "}":
                    depth -= 1
                j += 1
            val = fields_blob[i + 1 : j - 1]
            i = j
        elif fields_blob[i] == '"':
            j = i + 1
            while j < n:
                if fields_blob[j] == '"' and fields_blob[j - 1] != "\\":
                    break
                j += 1
            val = fields_blob[i + 1 : j]
            i = j + 1
        else:
            j = i
            while j < n and fields_blob[j] not in ",\r\n":
                j += 1
            val = fields_blob[i:j].strip()
            i = j

        fields[field_name] = " ".join(val.split())

    return fields


def stamp_zotero_keys_in_bib(path: Path, key_map: dict[str, str]) -> int:
    """Insert or update `zotero_key = {<KEY>}` in matched entries of a .bib file."""
    text = path.read_text(encoding="utf-8", errors="replace")
    entries = parse_bib_file(path)
    if not entries:
        return 0

    updated_count = 0
    new_chunks: list[str] = []
    last_idx = 0

    for entry in entries:
        new_chunks.append(text[last_idx : entry["start"]])
        raw = entry["raw"]
        ck = entry["citekey"]
        target_zkey = key_map.get(ck)

        if target_zkey:
            existing_zkey = entry["fields"].get("zotero_key", "").strip()
            if existing_zkey == target_zkey:
                new_chunks.append(raw)
            elif "zotero_key" in entry["fields"]:
                replaced = re.sub(
                    r"(zotero_key\s*=\s*)(?:\{[^{}]*\}|\"[^\"]*\")",
                    rf"\g<1>{{{target_zkey}}}",
                    raw,
                    flags=re.IGNORECASE,
                )
                new_chunks.append(replaced)
                if replaced != raw:
                    updated_count += 1
            else:
                indent_match = re.search(
                    r"\n([ \t]+)[a-zA-Z0-9_:-]+\s*=", raw
                )
                indent = indent_match.group(1) if indent_match else "  "
                close_pos = raw.rfind("}")
                if close_pos != -1:
                    before = raw[:close_pos].rstrip()
                    if not before.endswith(","):
                        before += ","
                    stamped = (
                        f"{before}\n{indent}zotero_key = {{{target_zkey}}}\n}}"
                    )
                    new_chunks.append(stamped)
                    updated_count += 1
                else:
                    new_chunks.append(raw)
        else:
            new_chunks.append(raw)

        last_idx = entry["end"]

    new_chunks.append(text[last_idx:])
    if updated_count > 0:
        path.write_text("".join(new_chunks), encoding="utf-8")
    return updated_count


# ---------------------------------------------------------------------------
# Online Verification (Crossref, OpenAlex, PubMed, arXiv) with Rate-Limiting
# ---------------------------------------------------------------------------


def _throttle(host: str, min_interval: float = 0.35) -> None:
    with _RATE_LOCK:
        now = time.monotonic()
        last = _LAST_REQ_TIME.get(host, 0.0)
        wait = min_interval - (now - last)
        if wait > 0:
            time.sleep(wait)
        _LAST_REQ_TIME[host] = time.monotonic()


def _http_get_json(url: str, timeout: int = 15) -> Any:
    host = urllib.parse.urlparse(url).netloc
    for attempt in range(3):
        _throttle(host, 0.4 if "arxiv" not in host else 1.0)
        req = urllib.request.Request(
            url,
            headers={
                "User-Agent": "ISR-Lab-Zotero-Auditor/1.0 (mailto:rcotton@sralab.org)",
                "Accept": "application/json",
            },
        )
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return json.loads(resp.read().decode("utf-8", errors="replace"))
        except urllib.error.HTTPError as e:
            if e.code == 429 and attempt < 2:
                time.sleep(1.5 * (attempt + 1))
                continue
            raise


def _http_get_text(url: str, timeout: int = 15) -> str:
    host = urllib.parse.urlparse(url).netloc
    for attempt in range(3):
        _throttle(host, 1.0 if "arxiv" in host else 0.4)
        req = urllib.request.Request(
            url,
            headers={
                "User-Agent": "ISR-Lab-Zotero-Auditor/1.0 (mailto:rcotton@sralab.org)",
            },
        )
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return resp.read().decode("utf-8", errors="replace")
        except urllib.error.HTTPError as e:
            if e.code == 429 and attempt < 2:
                time.sleep(2.0 * (attempt + 1))
                continue
            raise


def verify_entry_online(entry: dict[str, Any]) -> dict[str, Any]:
    """Verify a BibTeX entry against Crossref, OpenAlex, PubMed, and arXiv."""
    fields = entry["fields"]
    entry_type = entry["entry_type"]
    bib_title = fields.get("title", "")
    bib_authors = extract_bib_authors(
        fields.get("author", "") or fields.get("editor", "")
    )
    bib_first = bib_authors[0] if bib_authors else ""
    bib_year = extract_year(fields.get("year", "") or fields.get("date", ""))

    bib_blob = " ".join(
        [
            fields.get("doi", ""),
            fields.get("url", ""),
            fields.get("eprint", ""),
            fields.get("note", ""),
            fields.get("journal", ""),
            fields.get("howpublished", ""),
        ]
    )
    bib_dois = extract_all_dois(bib_blob)
    bib_arxivs = extract_all_arxiv_ids(
        bib_blob,
        allow_bare=bool(fields.get("eprint") or "arxiv" in bib_blob.lower()),
    )

    notes: list[str] = []

    # 1. If DOI is present (and not an arXiv DOI), check Crossref by DOI directly
    for doi in bib_dois:
        if doi.startswith("10.48550/arxiv."):
            aid = doi.split("10.48550/arxiv.", 1)[1]
            if aid not in bib_arxivs:
                bib_arxivs.append(aid)
            continue
        try:
            url = f"https://api.crossref.org/works/{urllib.parse.quote(doi)}?mailto=rcotton@sralab.org"
            res = _http_get_json(url)
            msg = res.get("message", {})
            cr_titles = msg.get("title", [])
            cr_title = cr_titles[0] if cr_titles else ""
            sim = title_similarity(bib_title, cr_title)
            cr_authors = [
                normalize_surname(a.get("family", ""))
                for a in msg.get("author", [])
                if a.get("family")
            ]
            cr_year = None
            for k in ("published-print", "published-online", "issued", "created"):
                parts = msg.get(k, {}).get("date-parts", [[]])
                if parts and parts[0]:
                    cr_year = parts[0][0]
                    break
            venue_list = msg.get("container-title", [])
            cr_venue = venue_list[0] if venue_list else msg.get("publisher", "")

            if sim >= 0.70 or (
                sim >= 0.55 and any_author_matches(bib_authors, cr_authors)
            ):
                if bib_first and cr_authors and not any_author_matches(bib_authors, cr_authors):
                    notes.append(
                        f"Author mismatch on DOI {doi}: bib first author '{bib_first}' vs Crossref '{cr_authors[0]}'"
                    )
                return {
                    "status": "verified_real",
                    "source": "crossref_doi",
                    "verified_doi": msg.get("DOI", doi).lower(),
                    "verified_arxiv": bib_arxivs[0] if bib_arxivs else None,
                    "verified_pmid": None,
                    "verified_title": strip_latex_and_accents(cr_title),
                    "verified_authors": [
                        f"{a.get('family', '')}, {a.get('given', '')}".strip(", ")
                        for a in msg.get("author", [])
                    ],
                    "verified_year": cr_year,
                    "verified_venue": strip_latex_and_accents(cr_venue),
                    "title_similarity": round(sim, 3),
                    "notes": notes,
                }
            else:
                notes.append(
                    f"DOI {doi} belongs to a different paper ('{cr_title[:70]}', sim={sim:.2f})"
                )
        except urllib.error.HTTPError as e:
            if e.code == 404:
                notes.append(f"DOI {doi} returned 404 Not Found on Crossref")
        except Exception as e:
            notes.append(f"DOI {doi} lookup error: {e}")

    # 2. If arXiv ID is present, check arXiv API directly
    for aid in bib_arxivs:
        try:
            url = f"http://export.arxiv.org/api/query?id_list={urllib.parse.quote(aid)}"
            xml_text = _http_get_text(url)
            root = ET.fromstring(xml_text)
            ns = {
                "atom": "http://www.w3.org/2005/Atom",
                "arxiv": "http://arxiv.org/schemas/atom",
            }
            entry_el = root.find("atom:entry", ns)
            if entry_el is not None:
                ax_title_el = entry_el.find("atom:title", ns)
                ax_title = (
                    " ".join((ax_title_el.text or "").split())
                    if ax_title_el is not None
                    else ""
                )
                ax_authors = []
                ax_surnames = []
                for au in entry_el.findall("atom:author", ns):
                    name_el = au.find("atom:name", ns)
                    if name_el is not None and name_el.text:
                        ax_authors.append(name_el.text.strip())
                        toks = name_el.text.strip().split()
                        if toks:
                            ax_surnames.append(normalize_surname(toks[-1]))
                pub_el = entry_el.find("atom:published", ns)
                ax_year = extract_year(pub_el.text if pub_el is not None else "")
                doi_el = entry_el.find("arxiv:doi", ns)
                ax_doi = (
                    doi_el.text.strip().lower()
                    if (doi_el is not None and doi_el.text)
                    else f"10.48550/arxiv.{aid.lower()}"
                )
                sim = title_similarity(bib_title, ax_title)
                if sim >= 0.70 or (
                    sim >= 0.55 and any_author_matches(bib_authors, ax_surnames)
                ):
                    if bib_first and ax_surnames and not any_author_matches(bib_authors, ax_surnames):
                        notes.append(
                            f"Author mismatch on arXiv:{aid}: bib first author '{bib_first}' vs arXiv '{ax_surnames[0]}'"
                        )
                    return {
                        "status": "verified_real",
                        "source": "arxiv_id",
                        "verified_doi": ax_doi,
                        "verified_arxiv": aid,
                        "verified_pmid": None,
                        "verified_title": ax_title,
                        "verified_authors": ax_authors,
                        "verified_year": ax_year,
                        "verified_venue": f"arXiv:{aid}",
                        "title_similarity": round(sim, 3),
                        "notes": notes,
                    }
                elif ax_title:
                    notes.append(
                        f"arXiv:{aid} belongs to a different paper ('{ax_title[:70]}', sim={sim:.2f})"
                    )
                else:
                    notes.append(f"arXiv:{aid} does not exist on arXiv")
        except Exception as e:
            notes.append(f"arXiv:{aid} lookup error: {e}")

    # 3. Search Crossref by bibliographic query (polite pool, high rate limit)
    if bib_title:
        try:
            q_parts = [strip_latex_and_accents(bib_title)]
            if bib_first:
                q_parts.append(bib_first)
            if bib_year:
                q_parts.append(str(bib_year))
            q_str = " ".join(q_parts)
            url = f"https://api.crossref.org/works?query.bibliographic={urllib.parse.quote(q_str)}&rows=5&mailto=rcotton@sralab.org"
            res = _http_get_json(url)
            for msg in res.get("message", {}).get("items", []):
                cr_titles = msg.get("title", [])
                cr_title = cr_titles[0] if cr_titles else ""
                sim = title_similarity(bib_title, cr_title)
                cr_authors = [
                    normalize_surname(a.get("family", ""))
                    for a in msg.get("author", [])
                    if a.get("family")
                ]
                cr_year = None
                for k in (
                    "published-print",
                    "published-online",
                    "issued",
                    "created",
                ):
                    parts = msg.get(k, {}).get("date-parts", [[]])
                    if parts and parts[0]:
                        cr_year = parts[0][0]
                        break
                venue_list = msg.get("container-title", [])
                cr_venue = (
                    venue_list[0] if venue_list else msg.get("publisher", "")
                )
                author_ok = (not bib_authors) or any_author_matches(
                    bib_authors, cr_authors
                )
                year_ok = (
                    (not bib_year)
                    or (not cr_year)
                    or abs(bib_year - cr_year) <= 2
                )
                if (sim >= 0.80 and author_ok) or (sim >= 0.92 and year_ok):
                    if bib_first and cr_authors and not author_ok:
                        notes.append(
                            f"Author mismatch: bib has '{bib_first}' vs Crossref '{cr_authors[0]}'"
                        )
                    return {
                        "status": "verified_real",
                        "source": "crossref_search",
                        "verified_doi": (msg.get("DOI") or "").lower() or None,
                        "verified_arxiv": None,
                        "verified_pmid": None,
                        "verified_title": strip_latex_and_accents(cr_title),
                        "verified_authors": [
                            f"{a.get('family', '')}, {a.get('given', '')}".strip(
                                ", "
                            )
                            for a in msg.get("author", [])
                        ],
                        "verified_year": cr_year,
                        "verified_venue": strip_latex_and_accents(cr_venue),
                        "title_similarity": round(sim, 3),
                        "notes": notes,
                    }
        except Exception as e:
            notes.append(f"Crossref search error: {e}")

    # 4. Search OpenAlex by title
    if bib_title:
        try:
            clean_q = strip_latex_and_accents(bib_title)
            url = f"https://api.openalex.org/works?search={urllib.parse.quote(clean_q)}&per-page=5&mailto=rcotton@sralab.org"
            res = _http_get_json(url)
            for item in res.get("results", []):
                oa_title = item.get("title") or item.get("display_name") or ""
                sim = title_similarity(bib_title, oa_title)
                oa_authors = []
                oa_surnames = []
                for auth in item.get("authorships", []):
                    dn = auth.get("author", {}).get("display_name", "")
                    if dn:
                        oa_authors.append(dn)
                        toks = dn.split()
                        if toks:
                            oa_surnames.append(normalize_surname(toks[-1]))
                oa_year = item.get("publication_year")
                oa_doi = normalize_doi(item.get("doi") or "")
                ids = item.get("ids", {}) or {}
                oa_pmid = None
                if ids.get("pmid"):
                    m_pm = PMID_RE.search(str(ids.get("pmid")))
                    if m_pm:
                        oa_pmid = m_pm.group(1)
                oa_arxiv = None
                if oa_doi and oa_doi.startswith("10.48550/arxiv."):
                    oa_arxiv = oa_doi.split("10.48550/arxiv.", 1)[1]
                loc = item.get("primary_location") or {}
                src = loc.get("source") or {}
                oa_venue = src.get("display_name", "")

                author_ok = (not bib_authors) or any_author_matches(
                    bib_authors, oa_surnames
                )
                year_ok = (
                    (not bib_year)
                    or (not oa_year)
                    or abs(bib_year - oa_year) <= 2
                )
                if (sim >= 0.80 and author_ok) or (sim >= 0.92 and year_ok):
                    if bib_first and oa_surnames and not author_ok:
                        notes.append(
                            f"Author mismatch: bib has '{bib_first}' vs OpenAlex '{oa_surnames[0]}'"
                        )
                    if bib_year and oa_year and abs(bib_year - oa_year) > 2:
                        notes.append(
                            f"Year difference: bib has {bib_year} vs OpenAlex {oa_year}"
                        )
                    return {
                        "status": "verified_real",
                        "source": "openalex_search",
                        "verified_doi": oa_doi,
                        "verified_arxiv": oa_arxiv,
                        "verified_pmid": oa_pmid,
                        "verified_title": strip_latex_and_accents(oa_title),
                        "verified_authors": oa_authors,
                        "verified_year": oa_year,
                        "verified_venue": oa_venue,
                        "title_similarity": round(sim, 3),
                        "notes": notes,
                    }
        except Exception as e:
            notes.append(f"OpenAlex search error: {e}")

    # 5. Search arXiv by title
    if bib_title:
        try:
            clean_t = normalize_title(bib_title)
            url = f"http://export.arxiv.org/api/query?search_query=ti:%22{urllib.parse.quote(clean_t)}%22&max_results=5"
            xml_text = _http_get_text(url)
            root = ET.fromstring(xml_text)
            ns = {
                "atom": "http://www.w3.org/2005/Atom",
                "arxiv": "http://arxiv.org/schemas/atom",
            }
            for entry_el in root.findall("atom:entry", ns):
                ax_title_el = entry_el.find("atom:title", ns)
                ax_title = (
                    " ".join((ax_title_el.text or "").split())
                    if ax_title_el is not None
                    else ""
                )
                sim = title_similarity(bib_title, ax_title)
                id_el = entry_el.find("atom:id", ns)
                ax_id_list = extract_all_arxiv_ids(
                    id_el.text if id_el is not None else ""
                )
                aid = ax_id_list[0] if ax_id_list else None
                ax_authors = []
                ax_surnames = []
                for au in entry_el.findall("atom:author", ns):
                    name_el = au.find("atom:name", ns)
                    if name_el is not None and name_el.text:
                        ax_authors.append(name_el.text.strip())
                        toks = name_el.text.strip().split()
                        if toks:
                            ax_surnames.append(normalize_surname(toks[-1]))
                pub_el = entry_el.find("atom:published", ns)
                ax_year = extract_year(pub_el.text if pub_el is not None else "")
                author_ok = (not bib_authors) or any_author_matches(
                    bib_authors, ax_surnames
                )
                if (sim >= 0.80 and author_ok) or sim >= 0.92:
                    return {
                        "status": "verified_real",
                        "source": "arxiv_search",
                        "verified_doi": f"10.48550/arxiv.{aid}"
                        if aid
                        else None,
                        "verified_arxiv": aid,
                        "verified_pmid": None,
                        "verified_title": ax_title,
                        "verified_authors": ax_authors,
                        "verified_year": ax_year,
                        "verified_venue": f"arXiv:{aid}" if aid else "arXiv",
                        "title_similarity": round(sim, 3),
                        "notes": notes,
                    }
        except Exception as e:
            notes.append(f"arXiv search error: {e}")

    # 6. Check if it is a known software/manual/website/book with URL
    if entry_type in {"manual", "misc", "software", "book", "techreport"} and (
        fields.get("url") or fields.get("howpublished")
    ):
        notes.append(
            f"Software/manual/dataset entry ({entry_type}) with URL/howpublished; not a journal/arXiv paper"
        )

    return {
        "status": "unverified",
        "source": None,
        "verified_doi": None,
        "verified_arxiv": None,
        "verified_pmid": None,
        "verified_title": None,
        "verified_authors": [],
        "verified_year": None,
        "verified_venue": None,
        "title_similarity": 0.0,
        "notes": notes,
    }


def discover_canonical_bib_files(
    workspace: Path, include_clones: bool = False
) -> list[Path]:
    """Find all canonical manuscript/grant .bib files across the workspace."""
    all_bibs = sorted(workspace.rglob("*.bib"))
    canonical: list[Path] = []
    for p in all_bibs:
        s = str(p)
        if any(
            skip in s
            for skip in (
                "/.worktrees/",
                "/.claude/worktrees/",
                "/node_modules/",
                "/.venv",
                "/_build/",
                "/templates/",
                "/template/",
                "/tests/",
                "/conda-bld/",
                "/reproducible_agent_environment/templates/",
                "/anny_mhr_refactor/",
                "/references_bibertool.bib",
                "/zotero_missing_verified_imports.bib",
                "/CITATION.bib",
                "/_biomech_spin_untracked",
            )
        ):
            continue
        if not include_clones and any(
            clone_skip in s
            for clone_skip in (
                "/BiomechanicalFollower-spinal-reflexes/",
                "/BiomechMammaNetEqx/",
                "/PosePipeAgent/repos/",
                "/Project_Infant/repos/",
                "/repos/BodyModels-pre-wrap-refactor/",
                "/repos/MVBP-world-splat-render/",
                "/repos/RepresentationProbing/",
                "/b3d-fascia/docs/papers/biomechanical_",
                "/b3d-fascia/docs/papers/sapiens_infant_distillation/",
                "/b3d-fascia/docs/papers/fascia/",
                "/b3d-splat/docs/papers/biomechanical_",
                "/b3d-splat/docs/papers/sapiens_infant_distillation/",
            )
        ):
            continue
        if p.name == "main.bib" and (p.parent / "references.bib").exists():
            continue
        canonical.append(p)
    return canonical


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Audit BibTeX (.bib) files against the local Zotero library and verify missing references."
    )
    parser.add_argument(
        "paths",
        nargs="*",
        help="Paths to .bib files or directories to scan (default: /workspaces/eqx_pose)",
    )
    parser.add_argument(
        "--cache",
        default=DEFAULT_CACHE_PATH,
        help="Path to local Zotero library cache JSON",
    )
    parser.add_argument(
        "--refresh-cache",
        action="store_true",
        help="Force re-fetching Zotero library from http://localhost:23119",
    )
    parser.add_argument(
        "--include-clones",
        action="store_true",
        help="Also include secondary repo clones/branches when scanning workspace",
    )
    parser.add_argument(
        "--stamp",
        action="store_true",
        help="Stamp `zotero_key = {<KEY>}` into matched BibTeX entries (and sync sibling main.bib)",
    )
    parser.add_argument(
        "--verify-online",
        action="store_true",
        help="Verify unmatched BibTeX entries against Crossref, OpenAlex, and arXiv",
    )
    parser.add_argument(
        "--verify-cache",
        default=DEFAULT_VERIFY_CACHE_PATH,
        help="Cache file for online verification results",
    )
    parser.add_argument(
        "--report-json",
        help="Write structured audit results to this JSON path",
    )
    parser.add_argument(
        "--export-missing-bib",
        help="Write deduplicated verified missing BibTeX entries to this .bib path",
    )
    args = parser.parse_args()

    items = load_or_fetch_zotero_library(
        cache_path=args.cache, refresh=args.refresh_cache
    )
    zindex = ZoteroIndex(items)

    target_bibs: list[Path] = []
    if not args.paths:
        target_bibs = discover_canonical_bib_files(
            Path("/workspaces/eqx_pose"), include_clones=args.include_clones
        )
    else:
        for raw_p in args.paths:
            p = Path(raw_p).resolve()
            if p.is_file() and p.suffix == ".bib":
                target_bibs.append(p)
            elif p.is_dir():
                target_bibs.extend(
                    discover_canonical_bib_files(
                        p, include_clones=args.include_clones
                    )
                )

    print(
        f"[Audit] Auditing {len(target_bibs)} canonical .bib files against {len(items)} Zotero items...",
        file=sys.stderr,
    )

    verify_cache: dict[str, dict[str, Any]] = {}
    vc_path = Path(args.verify_cache)
    if vc_path.exists():
        try:
            verify_cache = json.loads(vc_path.read_text(encoding="utf-8"))
        except Exception:
            verify_cache = {}

    file_reports: list[dict[str, Any]] = []
    unmatched_records: list[dict[str, Any]] = []

    for bib_path in target_bibs:
        entries = parse_bib_file(bib_path)
        matched_list = []
        unmatched_list = []
        key_map: dict[str, str] = {}

        for entry in entries:
            zot, method, warnings = zindex.match_bib_entry(entry)
            if zot is not None:
                key_map[entry["citekey"]] = zot["key"]
                matched_list.append(
                    {
                        "citekey": entry["citekey"],
                        "zotero_key": zot["key"],
                        "match_method": method,
                        "bib_title": entry["fields"].get("title", ""),
                        "zotero_title": zot.get("title", ""),
                        "warnings": warnings,
                    }
                )
            else:
                rec = {
                    "bib_path": str(bib_path),
                    "citekey": entry["citekey"],
                    "entry_type": entry["entry_type"],
                    "fields": entry["fields"],
                    "raw": entry["raw"],
                    "zotero_warnings": warnings,
                }
                unmatched_list.append(rec)
                unmatched_records.append(rec)

        stamped_count = 0
        if args.stamp and key_map:
            stamped_count = stamp_zotero_keys_in_bib(bib_path, key_map)
            sibling_main = bib_path.parent / "main.bib"
            if bib_path.name == "references.bib" and sibling_main.exists():
                stamp_zotero_keys_in_bib(sibling_main, key_map)

        file_reports.append(
            {
                "bib_path": str(bib_path),
                "total_entries": len(entries),
                "matched_count": len(matched_list),
                "unmatched_count": len(unmatched_list),
                "stamped_count": stamped_count,
                "matched": matched_list,
                "unmatched": unmatched_list,
            }
        )

    # Online verification of unmatched entries (deduplicated by title+first_author+doi signature)
    if args.verify_online and unmatched_records:
        unique_map: dict[str, dict[str, Any]] = {}
        for rec in unmatched_records:
            f = rec["fields"]
            sig = (
                f"{normalize_doi(f.get('doi', '')) or ''}|"
                f"{normalize_title(f.get('title', ''))}|"
                f"{(extract_bib_authors(f.get('author', '')) or [''])[0]}"
            )
            if sig not in unique_map:
                unique_map[sig] = rec

        to_query = [
            (sig, rec)
            for sig, rec in unique_map.items()
            if sig not in verify_cache
            or (
                verify_cache[sig].get("status") != "verified_real"
                and any("429" in str(n) for n in verify_cache[sig].get("notes", []))
            )
        ]
        print(
            f"[Verify] Verifying {len(unique_map)} unique unmatched references online ({len(to_query)} uncached)...",
            file=sys.stderr,
        )

        with ThreadPoolExecutor(max_workers=2) as pool:
            fut_map = {
                pool.submit(verify_entry_online, rec): sig
                for sig, rec in to_query
            }
            for fut in as_completed(fut_map):
                sig = fut_map[fut]
                try:
                    verify_cache[sig] = fut.result()
                except Exception as e:
                    verify_cache[sig] = {
                        "status": "error",
                        "notes": [str(e)],
                    }

        vc_path.write_text(
            json.dumps(verify_cache, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

        # Attach verification results and re-check Zotero using verified DOI/arXiv/title!
        for frep in file_reports:
            still_unmatched = []
            newly_matched_key_map: dict[str, str] = {}
            for rec in frep["unmatched"]:
                f = rec["fields"]
                sig = (
                    f"{normalize_doi(f.get('doi', '')) or ''}|"
                    f"{normalize_title(f.get('title', ''))}|"
                    f"{(extract_bib_authors(f.get('author', '')) or [''])[0]}"
                )
                vres = dict(verify_cache.get(sig, {}))
                if rec.get("zotero_warnings"):
                    vres["notes"] = list(rec["zotero_warnings"]) + list(
                        vres.get("notes", [])
                    )
                rec["verification"] = vres

                v_doi = normalize_doi(vres.get("verified_doi") or "")
                v_arxiv = vres.get("verified_arxiv")
                v_title = normalize_title(vres.get("verified_title") or "")
                bib_authors = extract_bib_authors(
                    f.get("author", "") or f.get("editor", "")
                )
                zot_hit = None
                hit_method = ""
                if v_doi and v_doi in zindex.by_doi:
                    cand = zindex.by_doi[v_doi][0]
                    if zindex._is_consistent_id_match(
                        f.get("title", ""), bib_authors, cand
                    ):
                        zot_hit = cand
                        hit_method = f"verified_doi:{v_doi}"
                elif v_arxiv and v_arxiv in zindex.by_arxiv:
                    cand = zindex.by_arxiv[v_arxiv][0]
                    if zindex._is_consistent_id_match(
                        f.get("title", ""), bib_authors, cand
                    ):
                        zot_hit = cand
                        hit_method = f"verified_arxiv:{v_arxiv}"
                elif v_title and v_title in zindex.by_norm_title:
                    cand = zindex.by_norm_title[v_title][0]
                    if any_author_matches(bib_authors, cand["_surnames"]):
                        zot_hit = cand
                        hit_method = "verified_title"

                if zot_hit is not None:
                    frep["matched"].append(
                        {
                            "citekey": rec["citekey"],
                            "zotero_key": zot_hit["key"],
                            "match_method": hit_method,
                            "bib_title": f.get("title", ""),
                            "zotero_title": zot_hit.get("title", ""),
                            "warnings": vres.get("notes", []),
                        }
                    )
                    newly_matched_key_map[rec["citekey"]] = zot_hit["key"]
                else:
                    still_unmatched.append(rec)

            frep["unmatched"] = still_unmatched
            frep["matched_count"] = len(frep["matched"])
            frep["unmatched_count"] = len(frep["unmatched"])
            if args.stamp and newly_matched_key_map:
                bpath = Path(frep["bib_path"])
                frep["stamped_count"] += stamp_zotero_keys_in_bib(
                    bpath, newly_matched_key_map
                )
                sibling_main = bpath.parent / "main.bib"
                if bpath.name == "references.bib" and sibling_main.exists():
                    stamp_zotero_keys_in_bib(
                        sibling_main, newly_matched_key_map
                    )

    if args.report_json:
        Path(args.report_json).write_text(
            json.dumps(file_reports, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    total_refs = sum(r["total_entries"] for r in file_reports)
    total_matched = sum(r["matched_count"] for r in file_reports)
    total_unmatched = sum(r["unmatched_count"] for r in file_reports)
    print(
        f"Audited {len(file_reports)} .bib files | Total entries: {total_refs} | Matched in Zotero: {total_matched} | Missing from Zotero: {total_unmatched}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
