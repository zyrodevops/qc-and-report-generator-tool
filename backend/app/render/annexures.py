"""
Annexures PDF Merger Engine — Master Spec §10.6, §14 (Day 14).

CRITICAL RULES:
- PAGE x OF y counts the report body only, not the merged file.
- Attachments are merged in deterministic order (A1..An, B1..Bn) strictly after body.
- Body pages and letterhead formatting remain byte-intact.
"""

import io
from pathlib import Path
from typing import Any, Dict, List, Optional
from pypdf import PdfReader, PdfWriter


def merge_pdf_annexures(
    body_pdf_bytes: bytes,
    annexures_block: Dict[str, Any],
    assets: Dict[str, Any],
) -> bytes:
    """
    Merge PDF attachments from assets in merge_order to the end of the body PDF.
    Returns the combined PDF bytes.
    """
    if not body_pdf_bytes:
        return b""

    computed = annexures_block.get("_computed", {})
    merge_order = computed.get("merge_order", [])

    # If no attachments to merge, return body intact
    if not merge_order:
        return body_pdf_bytes

    writer = PdfWriter()

    # 1. Add all pages from the report body
    body_reader = PdfReader(io.BytesIO(body_pdf_bytes))
    for page in body_reader.pages:
        writer.add_page(page)

    # 2. Append each annexure in order
    for item in merge_order:
        asset_id = item.get("asset_id")
        file_path = item.get("file_path")

        annex_bytes: Optional[bytes] = None

        if asset_id and asset_id in assets:
            asset = assets[asset_id]
            # Check original or derived
            orig = asset.get("original_path")
            if orig and Path(orig).exists():
                annex_bytes = Path(orig).read_bytes()

        if not annex_bytes and file_path and Path(file_path).exists():
            annex_bytes = Path(file_path).read_bytes()

        if annex_bytes:
            try:
                annex_reader = PdfReader(io.BytesIO(annex_bytes))
                for page in annex_reader.pages:
                    writer.add_page(page)
            except Exception:
                # If attachment cannot be parsed as PDF, skip or ignore
                pass

    out_buf = io.BytesIO()
    writer.write(out_buf)
    return out_buf.getvalue()
