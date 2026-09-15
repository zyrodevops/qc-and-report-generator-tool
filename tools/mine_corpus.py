#!/usr/bin/env python3
"""
Corpus Mining Script — Master Spec §14 Day 1 & Week 1 R6.

Standalone throwaway script for empirical analysis of client reports.
Walks the archive directory and produces:
  1. inventory.csv          — per-file metadata (report number, type, family, commodity, client, counts)
  2. block_sequences.csv    — heading sequence per report (discovers real template structures)
  3. sentence_frequency.csv — wording library seed (anonymised sentences sorted by frequency)
  4. defect_categories.csv  — table column headers per commodity
  5. arithmetic_errors.csv  — recomputed totals and percentages that disagree with document
  6. template_archetypes.json — prefill definitions per commodity for report auto-generation

Usage:
    python tools/mine_corpus.py <corpus_dir> [--output-dir <dir>]

CRITICAL-RULES compliance:
    - Reads files but writes nothing back to the corpus.
    - Text extracted to local cache (<output_dir>/.text_cache/); corpus read once.
    - Supports .pdf (pdfplumber/pypdf), .docx (python-docx), and .doc (libreoffice headless).
    - De-duplicates by report number + content hash.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
from collections import Counter, defaultdict
from concurrent.futures import ProcessPoolExecutor
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

# Optional imports with graceful fallbacks
try:
    import pdfplumber
    HAS_PDFPLUMBER = True
except ImportError:
    HAS_PDFPLUMBER = False

try:
    from docx import Document
    HAS_DOCX = True
except ImportError:
    HAS_DOCX = False


# ---------------------------------------------------------------------------
# Hashing & De-duplication
# ---------------------------------------------------------------------------

def compute_file_hash(data: bytes | Path) -> str:
    """Compute SHA-256 hash for byte contents or a file path."""
    if isinstance(data, Path):
        data = data.read_bytes()
    return hashlib.sha256(data).hexdigest()


# ---------------------------------------------------------------------------
# Regex patterns for Anonymisation
# ---------------------------------------------------------------------------

_RE_DATE = re.compile(
    r"\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b"
    r"|\b\d{4}-\d{2}-\d{2}\b"
    r"|\b\d{1,2}\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+20\d{2}\b",
    re.IGNORECASE
)
_RE_TEMP = re.compile(r"\b[-+]?\d+(\.\d+)?\s*°\s*C\b", re.IGNORECASE)
_RE_PERCENT = re.compile(r"\b\d+(\.\d+)?\s*%\b")
_RE_CONTAINER = re.compile(r"\b[A-Z]{4}\d{7}\b")
_RE_REPORT_NO = re.compile(r"\b(?:MCAPL|M|G)[-/\s]?\d+[-/\s]?(?:20\d{2}|\d{2}[A-Z]?)\b", re.IGNORECASE)
_RE_INVOICE_VAL = re.compile(r"\b(?:USD|US\$|INR|RS\.?|EUR|€|\$)\s*[\d,]+(\.\d{2})?\b", re.IGNORECASE)
_RE_NUMBER = re.compile(r"\b\d[\d,./]*\d\b|\b\d+\b")


def anonymise_sentence(sentence: str) -> str:
    """Replace PII/numbers/dates with standard placeholders."""
    s = _RE_INVOICE_VAL.sub("{CURRENCY}", sentence)
    s = _RE_CONTAINER.sub("{CONTAINER}", s)
    s = _RE_REPORT_NO.sub("{REPORT_NO}", s)
    s = _RE_TEMP.sub("{TEMP}", s)
    s = _RE_PERCENT.sub("{PERCENT}", s)
    s = _RE_DATE.sub("{DATE}", s)
    s = _RE_NUMBER.sub("{N}", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s


def is_valid_narrative_sentence(s: str) -> bool:
    """Filter out noise, table rows, headers, and footer lines."""
    s_clean = s.strip()
    if len(s_clean) < 30 or len(s_clean) > 350:
        return False
    s_upper = s_clean.upper()
    if any(ign in s_upper for ign in [
        "PAGE ", "MARINE CARGO AGENCIES", "FINAL SURVEY REPORT", "SURVEY PHOTO NO",
        "ATTENDANCE", "SR. NO", "IRDA/IND/SLA", "LICENCE NO", "LICENSE NO"
    ]):
        return False
    if s_clean.startswith((":", "|", "Total", "Sr.", "PHOTO", "Survey Photo")):
        return False
    words = re.findall(r"\b[a-zA-Z]{3,}\b", s_clean)
    if len(words) < 4:
        return False
    return True


# ---------------------------------------------------------------------------
# Text & Table Extraction per format
# ---------------------------------------------------------------------------

def _extract_pdf(path: Path) -> Dict[str, Any]:
    """Extract text, headings, and data tables from a .pdf file."""
    if not HAS_PDFPLUMBER:
        return {"text": "", "headings": [], "tables": [], "page_count": 0, "photo_count": 0}

    pages_text: List[str] = []
    tables: List[List[List[str]]] = []
    headings: List[str] = []
    photo_numbers: List[int] = []

    with pdfplumber.open(path) as pdf:
        page_count = len(pdf.pages)
        for i, page in enumerate(pdf.pages):
            txt = page.extract_text() or ""
            pages_text.append(txt)

            # Extract tables from first 6 pages where data and defect tables reside
            if i < 6:
                t_list = page.extract_tables() or []
                for t in t_list:
                    if t and len(t) >= 2:
                        cleaned_rows = [
                            [str(cell).replace("\n", " ").strip() if cell is not None else "" for cell in row]
                            for row in t
                        ]
                        tables.append(cleaned_rows)

            # Find photo numbers
            p_nums = re.findall(r"(?:Survey\s+Photo|Photo)\s+Nos?\.?\s*(\d+)", txt, re.IGNORECASE)
            for n in p_nums:
                try:
                    photo_numbers.append(int(n))
                except ValueError:
                    pass

    full_text = "\n".join(pages_text)

    # Detect headings
    headings.append("PARTICULARS")
    for p_txt in pages_text[:5]:
        for line in p_txt.splitlines():
            l = line.strip()
            if re.match(r"^(?:PARAGRAPH\s+\d+(\.\d+)?|SECTION\s+\d+)\s*[:\-]?", l, re.IGNORECASE):
                headings.append(re.sub(r"\s+", " ", l))
            elif re.match(r"^(?:NOTE|SURVEY\s+FINDINGS|THE\s+CONDITION\s+FOUND|CONDITION\s+FOUND|ATTENDANCE|SURVEY\s+PHOTOGRAPHS|PHOTOS\s+TAKEN|QC\s+INSPECTION\s+PHOTOGRAPHS|DEFECTS?\s+FOUND|REMARKS?|CONCLUSIONS?)\b", l, re.IGNORECASE) and len(l) < 60:
                if not any(ign in l.upper() for ign in ["PAGE", "MARINE CARGO AGENCIES", "PRIVATE LIMITED"]):
                    headings.append(re.sub(r"\s+", " ", l))

    photo_count = max(photo_numbers) if photo_numbers else len(re.findall(r"\(Photo No", full_text, re.IGNORECASE))

    return {
        "text": full_text,
        "headings": headings,
        "tables": tables,
        "page_count": page_count,
        "photo_count": photo_count,
    }


def _extract_docx(path: Path) -> Dict[str, Any]:
    """Extract text, headings, and data tables from a .docx file."""
    if not HAS_DOCX:
        return {"text": "", "headings": [], "tables": [], "page_count": 0, "photo_count": 0}

    doc = Document(str(path))
    headings: List[str] = ["PARTICULARS"]
    paragraphs: List[str] = []
    tables: List[List[List[str]]] = []

    for para in doc.paragraphs:
        txt = para.text.strip()
        if not txt:
            continue
        paragraphs.append(txt)

        if para.style.name.startswith("Heading"):
            headings.append(txt)
        elif re.match(r"^(?:PARAGRAPH\s+\d+(\.\d+)?|SECTION\s+\d+)\s*[:\-]?", txt, re.IGNORECASE):
            headings.append(txt)
        elif re.match(r"^(?:NOTE|SURVEY\s+FINDINGS|THE\s+CONDITION\s+FOUND|CONDITION\s+FOUND|ATTENDANCE|SURVEY\s+PHOTOGRAPHS|PHOTOS\s+TAKEN|QC\s+INSPECTION\s+PHOTOGRAPHS)\b", txt, re.IGNORECASE) and len(txt) < 60:
            headings.append(txt)

    for table in doc.tables:
        t_rows: List[List[str]] = []
        for row in table.rows:
            row_texts = [cell.text.replace("\n", " ").strip() for cell in row.cells]
            if any(t for t in row_texts):
                t_rows.append(row_texts)
        if t_rows:
            tables.append(t_rows)

    full_text = "\n".join(paragraphs)
    photo_count = len(re.findall(r"\(Photo No", full_text, re.IGNORECASE))
    page_count_approx = max(1, len(full_text) // 2500)

    return {
        "text": full_text,
        "headings": headings,
        "tables": tables,
        "page_count": page_count_approx,
        "photo_count": photo_count,
    }


def _extract_doc(path: Path) -> Dict[str, Any]:
    """Extract from legacy .doc via headless LibreOffice conversion to .docx."""
    with tempfile.TemporaryDirectory() as tmpdir:
        try:
            cmd = [
                "/usr/local/bin/libreoffice",
                "--headless",
                "--convert-to",
                "docx",
                str(path),
                "--outdir",
                tmpdir,
            ]
            res = subprocess.run(cmd, capture_output=True, text=True, timeout=45)
            if res.returncode == 0:
                conv_path = Path(tmpdir) / f"{path.stem}.docx"
                if conv_path.exists():
                    return _extract_docx(conv_path)
        except Exception:
            pass

    # Fallback to antiword if libreoffice fails
    try:
        result = subprocess.run(["antiword", str(path)], capture_output=True, text=True, timeout=30)
        text = result.stdout
        headings = [ln.strip() for ln in text.splitlines() if ln.strip() and ln.strip().isupper() and len(ln.strip()) > 4]
        return {
            "text": text,
            "headings": headings,
            "tables": [],
            "page_count": max(1, len(text) // 2500),
            "photo_count": len(re.findall(r"\(Photo No", text, re.IGNORECASE)),
        }
    except Exception:
        return {"text": "", "headings": [], "tables": [], "page_count": 0, "photo_count": 0}


def extract_cached_file(path: Path, cache_dir: Path) -> Dict[str, Any]:
    """Extract report content, utilizing SHA-256 keyed JSON cache for near-instant replays."""
    chash = compute_file_hash(path)[:16]
    cache_file = cache_dir / f"{chash}.json"

    if cache_file.exists():
        try:
            return json.loads(cache_file.read_text(encoding="utf-8"))
        except Exception:
            pass

    suffix = path.suffix.lower()
    if suffix == ".pdf":
        data = _extract_pdf(path)
    elif suffix == ".docx":
        data = _extract_docx(path)
    elif suffix == ".doc":
        data = _extract_doc(path)
    else:
        data = {"text": "", "headings": [], "tables": [], "page_count": 0, "photo_count": 0}

    data["content_hash"] = chash
    data["filename"] = path.name

    try:
        cache_file.write_text(json.dumps(data), encoding="utf-8")
    except Exception:
        pass

    return data


# ---------------------------------------------------------------------------
# Extraction of Metadata, Defect Columns, and Arithmetic Errors
# ---------------------------------------------------------------------------

COMMODITIES_LIST = [
    "mandarin", "orange", "apple", "grape", "kiwi", "pear", "plum",
    "cherry", "blueberry", "dragon", "avocado", "apricot", "machinery",
    "steel", "pulses", "general cargo"
]


def detect_report_meta(path: Path, data: Dict[str, Any]) -> Dict[str, Any]:
    """Parse report number, commodity, client, family, dates, and counts."""
    text = data.get("text", "")
    filename = path.name

    # 1. Report Number
    m_rep = _RE_REPORT_NO.search(filename)
    if not m_rep:
        m_rep = _RE_REPORT_NO.search(text[:1000])
    rep_no = m_rep.group(0).replace(" ", "-").upper() if m_rep else "UNKNOWN"

    # 2. Type & Family
    text_sample = text[:1500].lower()
    if "quality certificate" in text_sample or "qc report" in text_sample or "qc inspection" in text_sample or "qc" in filename.lower():
        rtype = "QC"
        family = "QC_REPORT"
    else:
        rtype = "SURVEY"
        family = "SURVEY_REPORT"

    # 3. Commodity
    commodity = "UNKNOWN"
    parent_name = path.parent.name.lower()
    for c in COMMODITIES_LIST:
        if c in parent_name:
            commodity = c.upper()
            break
    if commodity == "UNKNOWN":
        for c in COMMODITIES_LIST:
            if c in filename.lower() or c in text_sample:
                commodity = c.upper()
                break

    # 4. Client (Consignee)
    client = "UNKNOWN"
    m_client = re.search(r"Consignee[s]?\s*[:\t]\s*([^\n\r]+)", text[:2000], re.IGNORECASE)
    if m_client:
        client_cand = m_client.group(1).split(",")[0].strip()
        client_cand = re.sub(r"^[:\s\-]+", "", client_cand).strip()
        if len(client_cand) > 2 and not client_cand.upper().startswith("POLICY"):
            client = client_cand

    if client == "UNKNOWN":
        # Extract from filename e.g. "M-101-2026 NGK Trading..."
        fn_match = re.search(r"M-\d+-\d+\s+([A-Za-z0-9\s&]+?)(?:\s*\(|-|Container|#)", filename)
        if fn_match:
            client = fn_match.group(1).strip()

    # 5. Containers count
    cntrs = set(re.findall(r"\b[A-Z]{4}\d{7}\b", text[:3500]))
    container_count = max(len(cntrs), 1)

    # 6. Date
    date_match = _RE_DATE.search(text[:2000])
    date_str = date_match.group(0) if date_match else ""

    return {
        "filename": filename,
        "report_number": rep_no,
        "type": rtype,
        "family": family,
        "commodity": commodity,
        "client": client,
        "container_count": container_count,
        "photo_count": data.get("photo_count", 0),
        "page_count": data.get("page_count", 1),
        "date": date_str,
        "content_hash": data.get("content_hash", ""),
    }


def extract_defect_categories(tables: List[List[List[str]]], commodity: str) -> List[Tuple[str, str]]:
    """
    Extract defect column names found in tables matching quality keywords.
    Returns list of (clean_defect_name, raw_header_name).
    """
    defect_keywords = [
        "sound", "soft", "decay", "rotten", "russet", "pitting", "sunburn",
        "bruised", "mould", "damage", "shrivel", "scab", "scald", "chilling",
        "shatter", "bleached", "split", "cracked", "skin defects", "stem",
        "browning", "bitter-pit"
    ]
    extracted: List[Tuple[str, str]] = []

    for t in tables:
        for row in t[:3]:
            row_str = " ".join(str(c) for c in row if c).lower()
            if any(kw in row_str for kw in ["sound", "soft", "decay", "rotten", "russet", "damage"]):
                for cell in row:
                    c_str = str(cell).replace("\n", " ").strip()
                    c_lower = c_str.lower()
                    if any(kw in c_lower for kw in defect_keywords) and not c_lower.startswith(("total", "sr.", "no.")):
                        clean = re.sub(r"\s*\((?:Pcs|Kg|PCS|KG|%)\)", "", c_str, flags=re.IGNORECASE).strip()
                        clean = re.sub(r"^\d+\.\s*", "", clean).strip()
                        if clean and len(clean) >= 3:
                            extracted.append((clean.title(), c_str))
    return extracted


def check_table_arithmetic(
    tables: List[List[List[str]]],
    filename: str,
    commodity: str = "",
) -> List[Dict[str, Any]]:
    """
    Recompute row sums and verify against stated totals.
    Detects discrepancies where sum of defect cells disagrees with stated total.
    """
    errors: List[Dict[str, Any]] = []

    for t in tables:
        for row in t:
            row_clean_str = [str(c) if c is not None else "" for c in row]
            row_str = " ".join(row_clean_str).lower()
            if any(h in row_str for h in ["shipper", "invoice", "consignee", "represent", "bill of lading", "name", "designation", "ocean vessel"]):
                continue

            # Skip rows with container numbers in cells
            if re.search(r"[A-Z]{4}\d{7}", " ".join(row_clean_str)):
                continue

            is_pct_row = "percentage" in row_str or any("%" in c for c in row_clean_str)

            cells_clean = []
            for c in row_clean_str:
                c_str = c.replace("\n", " ").strip()
                m_pct = re.match(r"^([\d,.]+)\s*\([\d,.]+\s*%\)$", c_str)
                if m_pct:
                    c_str = m_pct.group(1)
                cells_clean.append(c_str)

            numeric_cells = []
            for cell in cells_clean:
                clean_num = re.sub(r"[^\d.]", "", cell.replace(",", ""))
                if clean_num and clean_num.count(".") <= 1:
                    try:
                        numeric_cells.append(Decimal(clean_num))
                    except InvalidOperation:
                        numeric_cells.append(None)
                else:
                    numeric_cells.append(None)

            valid = [v for v in numeric_cells if v is not None]
            if len(valid) < 3:
                continue

            if is_pct_row:
                # In percentage rows, check if sum is 100%
                if valid[-1] == Decimal("100"):
                    pct_sum = sum(valid[:-1])
                    if abs(pct_sum - Decimal("100")) <= Decimal("0.1"):
                        continue
                else:
                    pct_sum = sum(valid)
                    if abs(pct_sum - Decimal("100")) <= Decimal("0.1"):
                        continue

            if valid[-1] == Decimal("100") and len(valid) >= 4:
                stated_total = valid[-2]
                candidates = valid[:-2]
            else:
                stated_total = valid[-1]
                candidates = valid[:-1]

            if stated_total <= 0:
                continue

            computed_total = sum(candidates)

            # In tables where first column is box count or size, check candidates[1:] or candidates[2:]
            if len(candidates) > 1 and sum(candidates[1:]) == stated_total:
                continue
            if len(candidates) > 2 and sum(candidates[2:]) == stated_total:
                continue

            if computed_total != stated_total:
                chosen_comp = computed_total
                if len(candidates) > 1 and abs(sum(candidates[1:]) - stated_total) < abs(computed_total - stated_total):
                    chosen_comp = sum(candidates[1:])
                diff = abs(chosen_comp - stated_total)

                errors.append({
                    "filename": filename,
                    "row_preview": " | ".join(row_clean_str[:6]),
                    "computed_total": str(chosen_comp),
                    "stated_total": str(stated_total),
                    "difference": str(diff),
                })

    return errors


# ---------------------------------------------------------------------------
# CSV Helper
# ---------------------------------------------------------------------------

def _write_csv(path: Path, rows: List[Dict], fieldnames: List[str]) -> None:
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


# ---------------------------------------------------------------------------
# Mining Orchestrator
# ---------------------------------------------------------------------------

def _process_single_file(args_tuple: Tuple[Path, Path]) -> Dict[str, Any]:
    """Worker task: extracts data from one file and caches it."""
    file_path, cache_dir = args_tuple
    data = extract_cached_file(file_path, cache_dir)
    return {
        "path": str(file_path),
        "data": data,
    }


def mine_corpus(corpus_dir: Path, output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    cache_dir = output_dir / ".text_cache"
    cache_dir.mkdir(exist_ok=True)

    # Collect all supported files (.pdf, .docx, .doc)
    paths = (
        list(corpus_dir.glob("**/*.pdf"))
        + list(corpus_dir.glob("**/*.docx"))
        + list(corpus_dir.glob("**/*.doc"))
    )
    print(f"Found {len(paths)} reports in {corpus_dir}")

    # Extract all files in parallel
    worker_args = [(p, cache_dir) for p in sorted(paths)]
    print(f"Extracting & caching reports using ProcessPoolExecutor...")

    extracted_records: List[Dict[str, Any]] = []
    # If small number of files (e.g. tests), run serially for speed; else in parallel
    if len(paths) <= 10:
        for wa in worker_args:
            extracted_records.append(_process_single_file(wa))
    else:
        workers = min(8, os.cpu_count() or 4)
        with ProcessPoolExecutor(max_workers=workers) as executor:
            extracted_records = list(executor.map(_process_single_file, worker_args))

    print(f"Extraction complete. Analyzing {len(extracted_records)} records...")

    seen_keys: Set[Tuple[str, str]] = set()  # (report_number, content_hash) de-duplication

    inventory_rows: List[Dict[str, Any]] = []
    sequence_rows: List[Dict[str, Any]] = []
    sentence_counter: Counter = Counter()
    defect_cat_counter: Counter = Counter()
    defect_cat_samples: Dict[Tuple[str, str], str] = {}
    arith_errors: List[Dict[str, Any]] = []

    commodity_archetypes: Dict[str, Dict[str, Any]] = defaultdict(lambda: {
        "sequences": Counter(),
        "defect_columns": Counter(),
        "top_clauses": Counter(),
        "report_count": 0
    })

    for item in extracted_records:
        path = Path(item["path"])
        data = item["data"]
        text = data.get("text", "")
        headings = data.get("headings", [])
        tables = data.get("tables", [])
        chash = data.get("content_hash", compute_file_hash(path)[:16])

        if not text and not tables:
            continue

        meta = detect_report_meta(path, data)
        rep_no = meta["report_number"]
        dedup_key = (rep_no, chash)

        if dedup_key in seen_keys:
            continue
        seen_keys.add(dedup_key)

        # 1. Inventory Row
        inventory_rows.append(meta)

        # 2. Block Sequence
        clean_headings = []
        for h in headings[:15]:
            h_norm = re.sub(r"^(PARAGRAPH\s+\d+(\.\d+)?|SECTION\s+\d+)[:\s].*", r"\1", h, flags=re.IGNORECASE)
            h_norm = h_norm.strip()
            if h_norm and h_norm not in clean_headings:
                clean_headings.append(h_norm)

        seq_str = " → ".join(clean_headings) if clean_headings else "PARTICULARS → SURVEY NARRATIVE → DEFECT TABLE → PHOTOS"
        sequence_rows.append({
            "filename": path.name,
            "report_number": rep_no,
            "commodity": meta["commodity"],
            "type": meta["type"],
            "heading_sequence": seq_str,
        })
        commodity_archetypes[meta["commodity"]]["sequences"][seq_str] += 1
        commodity_archetypes[meta["commodity"]]["report_count"] += 1

        # 3. Sentence Frequency
        sentences = re.split(r"(?<=[.!?])\s+", text)
        for sent in sentences:
            if is_valid_narrative_sentence(sent):
                anon = anonymise_sentence(sent)
                sentence_counter[anon] += 1
                commodity_archetypes[meta["commodity"]]["top_clauses"][anon] += 1

        # 4. Defect Categories per Commodity
        defects = extract_defect_categories(tables, meta["commodity"])
        for clean_name, raw_name in defects:
            defect_cat_counter[(meta["commodity"], clean_name)] += 1
            defect_cat_samples[(meta["commodity"], clean_name)] = raw_name
            commodity_archetypes[meta["commodity"]]["defect_columns"][clean_name] += 1

        # 5. Arithmetic Errors
        errs = check_table_arithmetic(tables, path.name, meta["commodity"])
        arith_errors.extend(errs)

    # Prepare Output CSVs
    # 1. inventory.csv
    _write_csv(
        output_dir / "inventory.csv",
        inventory_rows,
        [
            "filename",
            "report_number",
            "type",
            "family",
            "commodity",
            "client",
            "container_count",
            "photo_count",
            "page_count",
            "date",
            "content_hash",
        ],
    )

    # 2. block_sequences.csv
    _write_csv(
        output_dir / "block_sequences.csv",
        sequence_rows,
        ["filename", "report_number", "commodity", "type", "heading_sequence"],
    )

    # 3. sentence_frequency.csv (top 200)
    top_sentences = [
        {"count": cnt, "sentence": sent}
        for sent, cnt in sentence_counter.most_common(200)
    ]
    _write_csv(
        output_dir / "sentence_frequency.csv",
        top_sentences,
        ["count", "sentence"],
    )

    # 4. defect_categories.csv
    defect_rows = []
    for (comm, cat), freq in defect_cat_counter.most_common():
        defect_rows.append({
            "commodity": comm,
            "defect_category": cat,
            "frequency": freq,
            "sample_header": defect_cat_samples.get((comm, cat), cat),
        })
    _write_csv(
        output_dir / "defect_categories.csv",
        defect_rows,
        ["commodity", "defect_category", "frequency", "sample_header"],
    )

    # 5. arithmetic_errors.csv
    _write_csv(
        output_dir / "arithmetic_errors.csv",
        arith_errors,
        ["filename", "row_preview", "computed_total", "stated_total", "difference"],
    )

    # 6. template_archetypes.json (for auto-prefilling new reports)
    archetypes_summary = {}
    for comm, arch in commodity_archetypes.items():
        if arch["report_count"] == 0:
            continue
        best_seq = arch["sequences"].most_common(1)[0][0] if arch["sequences"] else ""
        top_defects = [name for name, _ in arch["defect_columns"].most_common(8)]
        top_clauses = [cl for cl, _ in arch["top_clauses"].most_common(5)]
        unit = "kg" if comm in ["GRAPE", "GRAPES", "BLUEBERRY"] else "pcs"

        archetypes_summary[comm] = {
            "report_count": arch["report_count"],
            "heading_sequence": best_seq.split(" → "),
            "defect_columns": top_defects if top_defects else ["Sound", "Soft", "Rotten"],
            "unit": unit,
            "top_narrative_clauses": top_clauses,
        }

    (output_dir / "template_archetypes.json").write_text(
        json.dumps(archetypes_summary, indent=2), encoding="utf-8"
    )

    print(f"\n==================================================")
    print(f"Corpus Mining Complete! Results in: {output_dir}")
    print(f"==================================================")
    print(f"  1. inventory.csv          : {len(inventory_rows)} deduplicated reports")
    print(f"  2. block_sequences.csv    : {len(sequence_rows)} report block sequences")
    print(f"  3. sentence_frequency.csv : {len(top_sentences)} top wording clauses")
    print(f"  4. defect_categories.csv  : {len(defect_rows)} defect categories across commodities")
    print(f"  5. arithmetic_errors.csv  : {len(arith_errors)} mathematical discrepancies detected")
    print(f"  6. template_archetypes.json: Prefill schemas for {len(archetypes_summary)} commodities")
    print(f"==================================================\n")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Mine the client report corpus.")
    parser.add_argument("corpus_dir", type=Path, help="Directory containing .pdf/.docx/.doc reports")
    parser.add_argument("--output-dir", type=Path, default=Path("tools/corpus_output"),
                        help="Directory for output CSVs (default: tools/corpus_output)")
    args = parser.parse_args()

    if not args.corpus_dir.exists():
        print(f"ERROR: corpus_dir '{args.corpus_dir}' does not exist.", file=sys.stderr)
        sys.exit(1)

    mine_corpus(args.corpus_dir, args.output_dir)
