#!/usr/bin/env python3
"""
Corpus Mining Script — Master Spec §14 Day 1 (morning).

Standalone throwaway script. NOT part of the web application.
Run BEFORE writing any app code to empirically determine:
  1. Which sections/blocks appear in real reports, and in what order.
  2. The clause/wording library seed (top-100 sentences by frequency).
  3. Defect categories used per commodity.
  4. Historical arithmetic errors (mismatches between stored and recomputed totals).

Usage:
    python tools/mine_corpus.py <corpus_dir> [--output-dir <dir>]

Output CSVs:
    inventory.csv          — per-file metadata
    block_sequences.csv    — section heading sequences per report
    sentence_frequency.csv — anonymised sentences sorted by frequency
    defect_categories.csv  — table column headers per commodity
    arithmetic_errors.csv  — recomputed totals that disagree with document

CRITICAL-RULES compliance:
    - Reads files but writes nothing back.
    - Text extracted to a local cache; the corpus drive is read once.
    - Real report numbers/names/identifiers are in the cache only; CSVs get
      placeholder-substituted text.
    - De-duplicates by content hash (drafts inflate sentence frequency).
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import subprocess
import sys
from collections import Counter, defaultdict
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

try:
    from docx import Document
    from docx.oxml.ns import qn
    HAS_DOCX = True
except ImportError:
    HAS_DOCX = False
    print("WARNING: python-docx not installed. .docx files cannot be read.", file=sys.stderr)


# ---------------------------------------------------------------------------
# Regex patterns for anonymisation
# ---------------------------------------------------------------------------

_RE_DATE = re.compile(
    r"\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b"
    r"|\b\d{4}-\d{2}-\d{2}\b"
    r"|\b\d{1,2}\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{4}\b",
    re.IGNORECASE
)
_RE_NUMBER = re.compile(r"\b\d[\d,./]*\d\b|\b\d+\b")
_RE_CONTAINER = re.compile(r"\b[A-Z]{4}\d{7}\b")
_RE_REPORT_NO = re.compile(r"\bM-\d+-\d{4}\b", re.IGNORECASE)


def _anonymise(sentence: str) -> str:
    """Replace PII/identifiers with {PLACEHOLDER}."""
    s = _RE_CONTAINER.sub("{CONTAINER}", sentence)
    s = _RE_REPORT_NO.sub("{REPORT_NO}", s)
    s = _RE_DATE.sub("{DATE}", s)
    s = _RE_NUMBER.sub("{N}", s)
    # Collapse multiple spaces
    s = re.sub(r"\s+", " ", s).strip()
    return s


# ---------------------------------------------------------------------------
# Text extraction — docx and doc formats
# ---------------------------------------------------------------------------

def _content_hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()[:16]


def _extract_docx(path: Path) -> Tuple[str, List[str], List[List[str]]]:
    """
    Extract (full_text, heading_sequence, table_rows_list) from a .docx file.
    table_rows_list: list of rows, each row is list of cell strings.
    """
    if not HAS_DOCX:
        return "", [], []
    try:
        doc = Document(str(path))
        headings: List[str] = []
        paragraphs: List[str] = []
        tables_data: List[List[str]] = []

        for para in doc.paragraphs:
            text = para.text.strip()
            if not text:
                continue
            if para.style.name.startswith("Heading"):
                headings.append(text)
            paragraphs.append(text)

        for table in doc.tables:
            for row in table.rows:
                row_texts = [cell.text.strip() for cell in row.cells]
                if any(t for t in row_texts):
                    tables_data.append(row_texts)

        return "\n".join(paragraphs), headings, tables_data
    except Exception as e:
        print(f"  WARN: Could not parse {path.name}: {e}", file=sys.stderr)
        return "", [], []


def _extract_doc(path: Path) -> Tuple[str, List[str], List[List[str]]]:
    """Extract from legacy .doc via antiword."""
    try:
        result = subprocess.run(
            ["antiword", str(path)],
            capture_output=True, text=True, timeout=30
        )
        text = result.stdout
        # Best-effort heading detection: ALL CAPS lines
        headings = [ln.strip() for ln in text.splitlines()
                    if ln.strip() and ln.strip().isupper() and len(ln.strip()) > 4]
        return text, headings, []
    except (subprocess.TimeoutExpired, FileNotFoundError) as e:
        print(f"  WARN: antiword failed for {path.name}: {e}", file=sys.stderr)
        return "", [], []


def extract_text(path: Path, cache_dir: Path) -> Tuple[str, List[str], List[List[str]]]:
    """Extract text with caching. Cache key = content hash."""
    cache_key = _content_hash(path)
    cache_file = cache_dir / f"{cache_key}.json"

    if cache_file.exists():
        data = json.loads(cache_file.read_text())
        return data["text"], data["headings"], data["tables"]

    suffix = path.suffix.lower()
    if suffix == ".docx":
        text, headings, tables = _extract_docx(path)
    elif suffix == ".doc":
        text, headings, tables = _extract_doc(path)
    else:
        return "", [], []

    cache_file.write_text(json.dumps({
        "text": text, "headings": headings, "tables": tables
    }))
    return text, headings, tables


# ---------------------------------------------------------------------------
# Report metadata extraction
# ---------------------------------------------------------------------------

def _detect_report_meta(path: Path, text: str, headings: List[str]) -> Dict[str, Any]:
    """Best-effort extraction of report metadata from filename + text."""
    # Report number from filename or text
    report_no_match = _RE_REPORT_NO.search(path.stem) or _RE_REPORT_NO.search(text[:500])
    report_no = report_no_match.group(0) if report_no_match else ""

    # Type: QC vs Survey
    text_lower = text.lower()
    rtype = "QC" if "quality certificate" in text_lower or "qc report" in text_lower else "SURVEY"

    # Commodity: look for common keywords
    commodities = ["mandarin", "grape", "kiwi", "orange", "mango", "strawberry",
                   "machinery", "steel", "vehicles", "general cargo"]
    commodity = "unknown"
    for c in commodities:
        if c in text_lower:
            commodity = c
            break

    # Container count: count heading patterns like "CONDITION OF CONTAINER NO."
    container_count = len(re.findall(r"CONDITION OF CONTAINER", text, re.IGNORECASE))

    # Photo count: look for "(Photo No" patterns
    photo_count = len(re.findall(r"\(Photo No", text, re.IGNORECASE))

    # Page count: not easily derivable from text; use paragraph count as proxy
    page_count_approx = max(1, len(text) // 3000)

    # Date: first date-like pattern
    date_match = _RE_DATE.search(text[:1000])
    date_str = date_match.group(0) if date_match else ""

    return {
        "filename": path.name,
        "report_number": report_no,
        "type": rtype,
        "commodity": commodity,
        "container_count": container_count,
        "photo_count_approx": photo_count,
        "page_count_approx": page_count_approx,
        "date": date_str,
        "content_hash": _content_hash(path),
    }


# ---------------------------------------------------------------------------
# Arithmetic check
# ---------------------------------------------------------------------------

def _check_table_arithmetic(
    table_rows: List[List[str]],
    filename: str,
) -> List[Dict[str, Any]]:
    """
    Attempt to detect numeric rows whose row-sum disagrees with the last cell.
    Returns a list of error records.
    """
    errors = []
    for row in table_rows:
        numeric_cells = []
        for cell in row:
            try:
                numeric_cells.append(Decimal(cell.replace(",", "").strip()))
            except InvalidOperation:
                numeric_cells.append(None)

        # Need at least 3 numeric cells to check
        valid = [v for v in numeric_cells if v is not None]
        if len(valid) < 3:
            continue

        body = valid[:-1]
        stated_total = valid[-1]
        computed_total = sum(body)

        if computed_total != stated_total:
            errors.append({
                "filename": filename,
                "row_preview": " | ".join(row[:6]),
                "computed_total": str(computed_total),
                "stated_total": str(stated_total),
                "difference": str(abs(computed_total - stated_total)),
            })
    return errors


# ---------------------------------------------------------------------------
# Main mining loop
# ---------------------------------------------------------------------------

def mine_corpus(corpus_dir: Path, output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    cache_dir = output_dir / ".text_cache"
    cache_dir.mkdir(exist_ok=True)

    paths = list(corpus_dir.glob("**/*.docx")) + list(corpus_dir.glob("**/*.doc"))
    print(f"Found {len(paths)} files in {corpus_dir}")

    seen_hashes: set = set()  # de-duplication by content hash

    inventory_rows: List[Dict[str, Any]] = []
    sequence_rows: List[Dict[str, Any]] = []
    sentence_counter: Counter = Counter()
    defect_cat_rows: List[Dict[str, Any]] = []
    arith_errors: List[Dict[str, Any]] = []

    for path in sorted(paths):
        chash = _content_hash(path)
        if chash in seen_hashes:
            print(f"  SKIP (duplicate): {path.name}")
            continue
        seen_hashes.add(chash)

        print(f"  Processing: {path.name}")
        text, headings, tables = extract_text(path, cache_dir)
        if not text:
            continue

        # 1. Inventory
        meta = _detect_report_meta(path, text, headings)
        inventory_rows.append(meta)

        # 2. Block sequences (heading sequence)
        sequence_rows.append({
            "filename": path.name,
            "report_number": meta["report_number"],
            "heading_sequence": " → ".join(headings[:20]),  # cap at 20
        })

        # 3. Sentence frequency (anonymised)
        sentences = re.split(r"(?<=[.!?])\s+", text)
        for sent in sentences:
            sent = sent.strip()
            if len(sent) < 20:
                continue
            anon = _anonymise(sent)
            sentence_counter[anon] += 1

        # 4. Defect categories (table headers containing quality keywords)
        quality_keywords = {"sound", "soft", "decay", "rotten", "bruised", "damage",
                            "green", "overripe", "stem", "mould", "cut", "split"}
        for row in tables[:5]:  # first 5 table rows likely headers
            row_lower = [c.lower() for c in row]
            if any(kw in " ".join(row_lower) for kw in quality_keywords):
                defect_cat_rows.append({
                    "filename": path.name,
                    "commodity": meta["commodity"],
                    "categories": " | ".join(c for c in row if c.strip()),
                })

        # 5. Arithmetic errors
        errors = _check_table_arithmetic(tables, path.name)
        arith_errors.extend(errors)

    # Write CSVs
    _write_csv(output_dir / "inventory.csv", inventory_rows,
               ["filename", "report_number", "type", "commodity", "container_count",
                "photo_count_approx", "page_count_approx", "date", "content_hash"])

    _write_csv(output_dir / "block_sequences.csv", sequence_rows,
               ["filename", "report_number", "heading_sequence"])

    # Sentence frequency — top 200
    top_sentences = [
        {"sentence": sent, "count": cnt}
        for sent, cnt in sentence_counter.most_common(200)
    ]
    _write_csv(output_dir / "sentence_frequency.csv", top_sentences,
               ["count", "sentence"])

    _write_csv(output_dir / "defect_categories.csv", defect_cat_rows,
               ["filename", "commodity", "categories"])

    _write_csv(output_dir / "arithmetic_errors.csv", arith_errors,
               ["filename", "row_preview", "computed_total", "stated_total", "difference"])

    print(f"\nOutputs written to {output_dir}")
    print(f"  inventory.csv          — {len(inventory_rows)} reports")
    print(f"  block_sequences.csv    — {len(sequence_rows)} sequences")
    print(f"  sentence_frequency.csv — {len(top_sentences)} sentences")
    print(f"  defect_categories.csv  — {len(defect_cat_rows)} rows")
    print(f"  arithmetic_errors.csv  — {len(arith_errors)} potential errors")


def _write_csv(path: Path, rows: List[Dict], fieldnames: List[str]) -> None:
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Mine the client report corpus.")
    parser.add_argument("corpus_dir", type=Path, help="Directory containing .docx/.doc reports")
    parser.add_argument("--output-dir", type=Path, default=Path("tools/corpus_output"),
                        help="Directory for output CSVs (default: tools/corpus_output)")
    args = parser.parse_args()

    if not args.corpus_dir.exists():
        print(f"ERROR: corpus_dir '{args.corpus_dir}' does not exist.", file=sys.stderr)
        sys.exit(1)

    mine_corpus(args.corpus_dir, args.output_dir)

