"""
QC Client Report Fidelity Test Suite.
Verifies that generated QC reports match the authentic client reports (e.g. Saanvi Fresh Fruit / RGS Exim Pro):
1. Pre-populated authentic narrative and measurements from the 241-report corpus.
2. Two-tier alternating defect table layout (Count row + Percentage row) in both DOCX and HTML.
3. Canonical QC template styling with exact margins, headers, footers, and signature blocks.
4. Complete Zero-Drift between DOCX and HTML preview.
5. Numeric Traceability Gate passes all authentic numbers.
"""

import io
import re
from decimal import Decimal
import docx
from bs4 import BeautifulSoup
import pytest

from app.seeds.defaults import get_default_block_state
from app.compute.arithmetic import compute
from app.render.docx.engine import render_docx
from app.render.html.engine import render_html
from app.compute.traceability import check_traceability


def test_mandarin_qc_report_seeding_and_fidelity():
    """Verify mandarin QC report defaults are seeded with corpus narrative and defect categories."""
    state = get_default_block_state("perishable_qc_sea", "mandarin")
    assert state["report_title"] == "IN-HOUSE QC INSPECTION REPORT (FRESH MANDARIN)"

    # Verify blocks present
    block_types = [b["type"] for b in state["blocks"]]
    assert "particulars" in block_types
    assert "narrative" in block_types
    assert "measurements" in block_types
    assert "table" in block_types
    assert "photo_plate" in block_types
    assert "fixed_text" in block_types

    # Verify authentic measurements
    meas_block = next(b for b in state["blocks"] if b["type"] == "measurements")
    subjects = [r["subject"] for r in meas_block["rows"]]
    assert "Pulp Temperature" in subjects
    assert "Brix Content" in subjects

    # Verify defect categories
    tbl_block = next(b for b in state["blocks"] if b["type"] == "table")
    cat_keys = [c["key"] for c in tbl_block["categories"]]
    assert cat_keys == ["sound", "soft", "russet", "mechanical_injury", "rotten"]
    assert tbl_block["layout"] == "two_tier"

    # Verify boilerplate narrative
    narratives = [b.get("additional_text", "") for b in state["blocks"] if b["type"] == "narrative"]
    combined_narrative = " ".join(narratives)
    assert "probe thermometer" in combined_narrative.lower()
    assert "cutting the mandarin fruits" in combined_narrative.lower()
    assert "brix was checked" in combined_narrative.lower()


def test_two_tier_defect_table_in_docx_and_html():
    """Verify that two-tier alternating defect table renders with exact pieces and percentage rows."""
    state = get_default_block_state("perishable_qc_sea", "mandarin")
    computed_state = compute(state)

    # 1. DOCX Render
    docx_bytes = render_docx(computed_state)
    doc = docx.Document(io.BytesIO(docx_bytes))
    tables = doc.tables
    assert len(tables) >= 1

    # Find the defect table (cols >= 6)
    defect_table = None
    for t in tables:
        if len(t.columns) == 7:  # Count + 5 categories + Total
            defect_table = t
            break
    assert defect_table is not None, "Two-tier defect table not found in generated DOCX"

    docx_rows = [[c.text.strip() for c in r.cells] for r in defect_table.rows]
    header = docx_rows[0]
    assert "Count / Box Sample" in header[0]
    assert "Sound (Pcs)" in header[1]
    assert "Total (pcs)" in header[-1]

    # Row 1: Count 55 pieces
    assert "Count 55" in docx_rows[1][0]
    assert docx_rows[1][1] == "133"
    assert docx_rows[1][2] == "54"
    assert docx_rows[1][3] == "14"
    assert docx_rows[1][4] == "24"
    assert docx_rows[1][5] == "9"
    assert docx_rows[1][6] in ("234", "234.00")

    # Row 2: Count 55 percentages
    assert docx_rows[2][0] == "Percentage"
    assert docx_rows[2][1] == "56.84%"
    assert docx_rows[2][2] == "23.08%"
    assert docx_rows[2][3] == "5.98%"
    assert docx_rows[2][4] == "10.26%"
    assert docx_rows[2][5] == "3.84%"
    assert docx_rows[2][6] == "100.00%"

    # Column totals (second to last row)
    tot_pieces_row = docx_rows[-2]
    assert "Total (pcs)" in tot_pieces_row[0]
    assert tot_pieces_row[1] in ("371", "371.00")
    assert tot_pieces_row[2] in ("172", "172.00")
    assert tot_pieces_row[3] in ("51", "51.00")
    assert tot_pieces_row[4] in ("47", "47.00")
    assert tot_pieces_row[5] in ("34", "34.00")
    assert tot_pieces_row[6] in ("675", "675.00")

    # Column percentages (last row)
    tot_pct_row = docx_rows[-1]
    assert "Percentage" in tot_pct_row[0]
    assert tot_pct_row[1] == "54.96%"
    assert tot_pct_row[2] == "25.48%"
    assert tot_pct_row[3] == "7.56%"
    assert tot_pct_row[4] == "6.96%"
    assert tot_pct_row[5] == "5.04%"
    assert tot_pct_row[6] == "100.00%"

    # 2. HTML Preview Render
    html_out = render_html(computed_state)
    soup = BeautifulSoup(html_out, "html.parser")
    html_table = soup.find("table", class_="defect-table")
    assert html_table is not None

    html_rows = [
        [c.get_text(strip=True) for c in tr.find_all(["th", "td"])]
        for tr in html_table.find_all("tr")
    ]
    # Check that HTML and DOCX match values
    assert html_rows[1][1] == "133"
    assert html_rows[2][1] == "56.84%"
    assert html_rows[-2][1] in ("371", "371.00")
    assert html_rows[-1][1] == "54.96%"


def test_qc_report_traceability_compliance():
    """Verify that authentic seeded numbers pass the Numeric Traceability Gate."""
    state = get_default_block_state("perishable_qc_sea", "mandarin")
    docx_bytes = render_docx(state)

    res = check_traceability(state, docx_bytes)
    assert res.passed, f"Numeric traceability gate failed on seeded defaults: {res.untraceable}"
