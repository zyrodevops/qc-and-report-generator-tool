"""
Run the tally pipeline over the client's real sheets and report what came back.

  python scripts/test_tally_sheets.py                  # all sheets
  python _tools/test_tally_sheets.py --limit 5          # first five
  python _tools/test_tally_sheets.py --file WA0076      # one sheet
  python _tools/test_tally_sheets.py --json out.json    # full dump

Set GEMINI_API_KEY in the environment to exercise the cloud reader. Without it
the local engines run and the output shows what the fallback actually manages,
which is the honest baseline to compare against.

What the report tells you, per sheet:

  lines        how many rows came back
  subtotals    how many were identified as group subtotal lines
  ties out     subtotal lines whose cells add up to the total written on the
               sheet — this is the number that matters, because it is the only
               check that does not depend on trusting the reader
  mismatch     subtotal lines where they disagree
  gaps         cells that came back unreadable and need typing in

A sheet with every subtotal tying out has been read correctly, near enough to
certainty: the reader would have had to make several compensating errors across
a row for the arithmetic to still land on the surveyor's own figure.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
from pathlib import Path
from typing import Any, Dict, List

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "backend"))

SHEETS = Path(r"D:\marine-corpus\extracted\marine-cargo-tally\Marine cargo\Tally sheets")

# Which fruit each sheet is, where it is legible from the sheet itself. Used only
# to pick the columns offered; anything not listed is read without a commodity
# hint, which is also what happens when the surveyor has not chosen one yet.
KNOWN_COMMODITY: Dict[str, str] = {
    "IMG-20260903-WA0064.jpg": "MANDARIN",
    "IMG-20260903-WA0065.jpg": "ORANGE",
    "IMG-20260903-WA0076.jpg": "APPLE",
    "IMG-20260903-WA0118.jpg": "PEAR",
}


async def run_one(path: Path, commodity: str | None) -> Dict[str, Any]:
    from app.ingest.tally.pipeline import read_tally_sheet

    result = await read_tally_sheet(
        image_bytes=path.read_bytes(),
        filename=path.name,
        commodity=commodity,
    )

    rows: List[Dict[str, Any]] = result["table"]["rows"]
    subtotals = [r for r in rows if r.get("is_subtotal")]
    ties = [r for r in subtotals if (r.get("check") or {}).get("status") == "OK"]
    mismatched = [r for r in subtotals if (r.get("check") or {}).get("status") == "MISMATCH"]

    gaps = 0
    for r in rows:
        for d in (r.get("cell_details") or {}).values():
            if d.get("normalized_value") is None:
                gaps += 1

    return {
        "file": path.name,
        "commodity": commodity,
        "reader": (result.get("reader") or {}).get("used"),
        "reader_error": (result.get("reader") or {}).get("cloud_error"),
        "status": result["extraction_status"],
        "rows": len(rows),
        "subtotals": len(subtotals),
        "ties_out": len(ties),
        "mismatched": len(mismatched),
        "gaps": gaps,
        "columns": [c["label"] for c in result["table"]["categories"]],
        "extra_columns": (result.get("reader") or {}).get("extra_columns") or [],
        "headers": {k: v for k, v in (result.get("headers") or {}).items() if v is not None},
        "mismatch_detail": [
            {"group": r["group"], "computed": r["computed_total"],
             "stated": r["stated_total"], "delta": (r.get("check") or {}).get("delta")}
            for r in mismatched
        ],
        "_full": result,
    }


async def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--file", type=str, default="")
    ap.add_argument("--json", type=str, default="")
    ap.add_argument("--dir", type=str, default=str(SHEETS))
    args = ap.parse_args()

    folder = Path(args.dir)
    if not folder.exists():
        print(f"Sheet folder not found: {folder}")
        return 1

    files = sorted(p for p in folder.iterdir() if p.suffix.lower() in (".jpg", ".jpeg", ".png"))
    if args.file:
        files = [p for p in files if args.file.lower() in p.name.lower()]
    if args.limit:
        files = files[: args.limit]

    if not files:
        print("No matching sheets.")
        return 1

    from app.ingest.tally.cloud_reader import cloud_reader_configured
    from app.ingest.tally.pipeline import available_engines

    print("=" * 78)
    print(f"Sheets            : {len(files)}")
    print(f"Cloud reader      : {'configured' if cloud_reader_configured() else 'NOT configured'}")
    print(f"Local engines     : {available_engines() or 'none installed'}")
    print("=" * 78)

    results: List[Dict[str, Any]] = []
    for path in files:
        commodity = KNOWN_COMMODITY.get(path.name)
        try:
            r = await run_one(path, commodity)
        except Exception as exc:
            print(f"\n{path.name}: FAILED — {type(exc).__name__}: {exc}")
            continue

        results.append(r)
        flag = "ok " if r["mismatched"] == 0 and r["subtotals"] else "   "
        print(
            f"\n{flag}{r['file']}  [{r['commodity'] or 'no commodity'}]  via {r['reader']}"
            f"\n     status={r['status']}  lines={r['rows']}  subtotals={r['subtotals']}"
            f"  ties out={r['ties_out']}  mismatch={r['mismatched']}  gaps={r['gaps']}"
        )
        if r["headers"]:
            shown = {k: r["headers"][k] for k in list(r["headers"])[:5]}
            print(f"     header: {shown}")
        if r["extra_columns"]:
            print(f"     columns not in the fruit config: {r['extra_columns']}")
        for m in r["mismatch_detail"][:3]:
            print(f"     MISMATCH {m['group']}: cells={m['computed']} written={m['stated']} ({m['delta']:+})")

    # ---- summary ----------------------------------------------------------
    total_sub = sum(r["subtotals"] for r in results)
    total_tie = sum(r["ties_out"] for r in results)
    total_mis = sum(r["mismatched"] for r in results)
    total_gap = sum(r["gaps"] for r in results)
    read_ok = sum(1 for r in results if r["rows"] > 0)

    print("\n" + "=" * 78)
    print(f"Sheets returning any rows : {read_ok} / {len(results)}")
    print(f"Subtotal lines found      : {total_sub}")
    if total_sub:
        print(f"  tying out to the sheet  : {total_tie}  ({100 * total_tie / total_sub:.0f}%)")
        print(f"  disagreeing             : {total_mis}")
    print(f"Cells needing typing in   : {total_gap}")
    print("=" * 78)

    if args.json:
        Path(args.json).write_text(
            json.dumps([{k: v for k, v in r.items() if k != "_full"} for r in results],
                       indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        print(f"Written to {args.json}")

    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
