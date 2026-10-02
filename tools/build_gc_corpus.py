"""
Build the general cargo wording corpus: CORPUS_DIR/analysis/gc/corpus.jsonl

The client's general cargo wording comes from his previous firm's reports
(the "Gladstone" folder, as he asked). This picks the real survey reports out
of that folder and writes their paragraphs as clean text, one report a line:

    {"case": ..., "year": 23, "type": ..., "mode": "SEA", "paragraphs": [...]}

What is left out (nothing is deleted on disk):
  - fruit surveys: fruit wording comes from his own 439 fruit reports
  - documents that are not survey reports (policies, invoices, catalogues …)
  - scans and near-empty files, blank templates
  - duplicate copies of a case (the head-office corrected copy is kept)

Paragraphs are read from the Word file: old .doc files from their .docx copy
in CORPUS_DIR/analysis/gc-docx/<sha16>.docx (made with Word, see
analysis/gc-docx/convert.ps1), since the .doc text in the textcache breaks
sentences at the end of every printed line. Tables are left out: their cells
are figures, not wording.

Usage:  python tools/build_gc_corpus.py [CORPUS_DIR]
"""

from __future__ import annotations

import json
import os
import re
import sys
from collections import defaultdict
from pathlib import Path

CASE = re.compile(r"\bG\s*[/\-]\s*(\d{3,4})\s*[/\-]\s*(\d{2})\s*([A-Z]{1,3})\b")
SECTION_MARKS = [
    r"INTRODUCTION", r"APPLICATION", r"CIRCUMSTANCES?\s+OF\s+LOSS", r"\bCIRCUMSTANCES\b", r"OUR\s+(JOINT\s+)?SURVEY",
    r"SURVEY\s+FINDINGS", r"CAUSE\s+OF\s+(THE\s+)?(LOSS|DAMAGE)", r"NEXT\s+STEP", r"DOCUMENTATION", r"CLAIM\s+RESERVE",
    r"NARRATIVE\s+SECTION", r"GENERAL\s+INFORMATION", r"SURVEY\s+DETAILS", r"\bFINDINGS\b", r"\bCONCLUSION\b",
    r"EXTENT\s+OF\s+(THE\s+)?(LOSS|DAMAGE)", r"NATURE\s+OF\s+PACKING", r"CONDITION\s+FOUND", r"SURVEY\s+PARTICIPANTS",
    r"COURSE\s+OF\s+TRANSPORT", r"DAMAGE\s+ASSESSMENT", r"IDENTIFICATION\s+OF\s+GOODS", r"BACKGROUND\s+INFORMATION",
    r"PERSONS?\s+PRESENT|ATTENDED\s+BY|FOLLOWING\s+PERSONS", r"INVESTIGATION\s+FINDINGS|OUR\s+INVESTIGATION",
]
TEMPLATE = re.compile(
    r"complete with|replace the red colou?red|\[insert|<<\s*name|xx/xx/|dd/mm/yyyy|\bxxxx\b|please fill|to be filled|"
    r"enter (the )?(name|date|number)|name of (the )?surveyor here|\(tick\)|☐|□\s*others", re.I)
FRUIT = re.compile(r"\b(apples?|grapes?|kiwi|pears?|oranges?|mandarins?|cherr(y|ies)|plums?|avocados?|dragon ?fruits?|"
                   r"blueberr(y|ies)|pomegranates?|bananas?|pulp temperature|brix|punnets?|fresh fruits?)\b", re.I)
FRUIT_NAME = re.compile(r"^\s*(\d\.\)\s*)?(APPLE|KIWI|PEAR|ORANGE|GRAPES?|MANDARINS?|CHERR|PLUM|AVOCADO|DRAGON|BLUEBERR|APRICOT)\b", re.I)


def report_type(t: str, fn: str) -> str:
    h = (fn + " " + t[:3000]).upper()
    if re.search(r"NAME OF THE CONSIGNEE OF GOODS|NARRATIVE SECTION", t.upper()) and "PRELIMINARY SURVEY REPORT" not in h:
        return "survey_report_form"
    if re.search(r"FINAL\s+(SURVEY\s+)?REPORT", h):
        return "final"
    if re.search(r"PRELIMINARY|PRELIMINAY|\bPLA\b|INITIAL LOSS ADVICE", h):
        return "preliminary"
    if re.search(r"JOINT\s+SURVEY", h):
        return "joint_survey"
    if re.search(r"LOADING|LASHING|STOWAGE|STUFFING|PRE[\s-]*SHIPMENT", h):
        return "loading"
    return "other"


def mode_of(t: str) -> str:
    return "AIR" if re.search(r"\bflight\b|\bairport\b|airway bill|air waybill|\bawb\b|air cargo complex", t, re.I) else "SEA"


def case_of(fn: str, t: str) -> tuple[str, int | None]:
    m = CASE.search(fn) or CASE.search(t[:4000])
    if m:
        return f"G-{m.group(1)}-{m.group(2)}{m.group(3)}", int(m.group(2))
    bt = re.search(r"\bGM-[A-Z]{2}-\d{5,7}(?:-\d{2})?\b", fn + " " + t[:4000])
    if bt:
        return "BT " + bt.group(0), None
    stem = re.sub(r"\.(docx?|pdf|dotx?)$", "", fn, flags=re.I)
    stem = re.sub(r"\(.*?\)|\{.*?\}|\b(copy|corrected|final|draft|version|new|revised|h\.?o\.?)\b|[^a-z]", "", stem.lower())
    return "FILE " + stem[:40], None


def usable(d: dict) -> bool:
    t = d.get("text") or ""
    fn = d.get("filename", "")
    if d.get("subfolder") == "3.) FRUITS SURVEYS" or FRUIT_NAME.match(fn) or len(FRUIT.findall(t)) >= 8:
        return False
    if len(t.strip()) < 1500:
        return False
    marks = sum(1 for rx in SECTION_MARKS if re.search(rx, t, re.I))
    has_case = bool(CASE.search(fn) or CASE.search(t[:4000]))
    if not (marks >= 3 or (has_case and marks >= 1 and len(t) >= 2500) or (report_type(t, fn) != "other" and marks >= 2)):
        return False
    if len(TEMPLATE.findall(t)) >= 3 or (re.search(r"template|blank .*form|\bformat\b|\bsample of\b|\bxxx\b", fn, re.I) and not has_case):
        return False
    return True


def docx_paragraphs(path: Path) -> list[str]:
    import docx

    d = docx.Document(str(path))
    out = []
    for p in d.paragraphs:
        s = " ".join(p.text.split())
        if not s:
            continue
        if p.style is not None and p.style.name and p.style.name.lower().startswith("list"):
            s = "• " + s
        out.append(s)
    return out


def text_paragraphs(t: str) -> list[str]:
    # PDFs: the text layer, joined back into paragraphs at blank lines.
    out = []
    for block in re.split(r"\n\s*\n", t):
        lines = [l for l in block.splitlines() if l.count("|") < 2]
        s = " ".join(" ".join(lines).split())
        if s:
            out.append(s)
    return out


def main(corpus: str) -> None:
    corpus_p = Path(corpus)
    extracted = corpus_p / "extracted"
    conv = corpus_p / "analysis" / "gc-docx"
    docs = []
    for f in sorted((corpus_p / "textcache").glob("*.json")):
        d = json.loads(f.read_text(encoding="utf-8"))
        if d.get("folder") == "general-cargo" and usable(d):
            docs.append(d)

    # one file per case and report type: the corrected copy, else the longest
    groups = defaultdict(list)
    for d in docs:
        case, _ = case_of(d["filename"], d.get("text") or "")
        groups[(case, report_type(d.get("text") or "", d["filename"]))].append(d)
    keep = []
    for (case, typ), ds in groups.items():
        ds.sort(key=lambda d: ("Corrected" not in (d.get("subfolder") or ""), -len(d.get("text") or "")))
        keep.append((case, typ, ds[0]))

    out_dir = corpus_p / "analysis" / "gc"
    out_dir.mkdir(parents=True, exist_ok=True)
    n_docx = n_text = 0
    with open(out_dir / "corpus.jsonl", "w", encoding="utf-8") as w:
        for case, typ, d in keep:
            t = d.get("text") or ""
            ext = d["ext"].lower()
            paras = None
            path = None
            if ext in (".docx", ".dotx"):
                path = extracted / d["rel"]
            elif ext in (".doc", ".dot"):
                path = conv / (d["sha"][:16] + ".docx")
            if path is not None and path.exists():
                try:
                    paras = docx_paragraphs(path)
                    n_docx += 1
                except Exception:
                    paras = None
            if not paras:
                paras = text_paragraphs(t)
                n_text += 1
            _, year = case_of(d["filename"], t)
            w.write(json.dumps({"case": case, "year": year, "type": typ, "mode": mode_of(t), "sha": d["sha"][:16],
                                "paragraphs": paras}, ensure_ascii=False) + "\n")
    print(f"{len(keep)} reports written to {out_dir / 'corpus.jsonl'} ({n_docx} from Word paragraphs, {n_text} from text)")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else os.environ.get("CORPUS_DIR", "D:/marine-corpus"))
