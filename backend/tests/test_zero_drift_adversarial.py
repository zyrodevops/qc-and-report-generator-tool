"""
Adversarial Stress Test Suite for Milestone 1 Zero-Drift Guarantee.
Challenger 1: Tests extreme boundary conditions, edge cases, large numbers,
rounding precision, Hare-Niemeyer tie-breaking, and photo lists scaling.
"""

from __future__ import annotations

from decimal import Decimal
import io
import re
from typing import Any, Dict, List
import pytest

from app.compute.arithmetic import compute, compute_table, _hare_niemeyer
from app.compute.photo_ranges import compute_photo_ranges
from app.render.docx.engine import render_docx, render_table
from app.render.html.engine import render_html, render_table_html
from backend.tests.test_zero_drift_preview import (
    extract_docx_data,
    extract_html_data,
    assert_zero_drift,
)
import docx
from bs4 import BeautifulSoup


# ===========================================================================
# 1. Defect Tables: Empty, Single-Cell, and All-Zeros Tables
# ===========================================================================

def test_adversarial_empty_table_zero_categories_bug_reproduction():
    """
    BUG REPRODUCTION FINDING:
    Defect table with 0 categories (categories: []) causes compute_table to crash with:
    AttributeError: 'int' object has no attribute 'quantize'
    at backend/app/compute/arithmetic.py line 128:
        grand_total = sum(col_totals_rounded.values())
    Python's built-in sum() on an empty sequence defaults to integer 0, which cannot be quantized.
    Fix: use sum(col_totals_rounded.values(), Decimal(0)).
    """
    state = {
        "metadata": {"number": "ADV-001", "docx_template": "mca-qc-synthetic.docx"},
        "blocks": [
            {
                "id": "tbl_empty_0x0",
                "type": "table",
                "title": "Completely Empty Table",
                "unit": "pcs",
                "grouping_label": "Group",
                "categories": [],
                "rows": [],
            }
        ],
    }

    with pytest.raises(AttributeError) as excinfo:
        render_docx(state)
    assert "'int' object has no attribute 'quantize'" in str(excinfo.value)


def test_adversarial_empty_table_zero_categories_render_simulation():
    """
    Simulates zero-drift rendering for empty table (0 categories) once compute_table provides Decimal(0).
    Verifies that the underlying DOCX and HTML table renderers produce identical 3x3 grids.
    """
    block = {
        "type": "table",
        "title": "Empty Table",
        "unit": "pcs",
        "categories": [],
        "rows": [],
    }
    computed = {
        "row_totals": [],
        "row_percentages": [],
        "column_totals": {},
        "grand_total": Decimal("0.00"),
        "column_percentages": {},
    }

    # DOCX rendering
    doc = docx.Document()
    render_table(doc, block, computed)
    t = doc.tables[0]
    docx_grid = [[c.text.strip() for c in r.cells] for r in t.rows]

    # HTML rendering
    html_out = render_table_html(block, computed)
    soup = BeautifulSoup(html_out, "html.parser")
    html_table = soup.find("table")
    html_grid = [
        [c.get_text(strip=True) for c in tr.find_all(["th", "td"])]
        for tr in html_table.find_all("tr")
    ]

    expected_grid = [
        ["Group", "Total (pcs)", "%"],
        ["Total", "0.00", ""],
        ["%", "", ""],
    ]
    assert docx_grid == expected_grid
    assert html_grid == expected_grid
    assert docx_grid == html_grid


def test_adversarial_empty_table_with_categories_zero_rows():
    """Defect table with categories defined but zero data rows."""
    state = {
        "metadata": {"number": "ADV-002", "docx_template": "mca-qc-synthetic.docx"},
        "blocks": [
            {
                "id": "tbl_empty_rows",
                "type": "table",
                "title": "Empty Rows Table",
                "unit": "pcs",
                "grouping_label": "Lot",
                "categories": [
                    {"key": "sound", "label": "Sound"},
                    {"key": "bruised", "label": "Bruised"},
                    {"key": "decay", "label": "Decay"},
                ],
                "rows": [],
            }
        ],
    }

    docx_bytes = render_docx(state)
    html_content = render_html(state)

    assert_zero_drift(docx_bytes, html_content)

    docx_data = extract_docx_data(docx_bytes)
    html_data = extract_html_data(html_content)

    tab = docx_data["defect_tables"][0]
    assert tab["row_totals"] == []
    assert tab["col_totals"] == ["0.00", "0.00", "0.00"]
    assert tab["grand_total"] == "0.00"
    assert tab["col_pcts"] == ["0.00", "0.00", "0.00"]
    assert tab["full_grid"] == html_data["defect_tables"][0]["full_grid"]


def test_adversarial_empty_table_unit_kg_3dp():
    """Empty defect table with unit 'kg' requiring 3-decimal precision."""
    state = {
        "metadata": {"number": "ADV-003", "docx_template": "mca-qc-synthetic.docx"},
        "blocks": [
            {
                "id": "tbl_empty_kg",
                "type": "table",
                "title": "Empty KG Table",
                "unit": "kg",
                "grouping_label": "Batch",
                "categories": [
                    {"key": "grade_a", "label": "Grade A (kg)"},
                    {"key": "grade_b", "label": "Grade B (kg)"},
                ],
                "rows": [],
            }
        ],
    }

    docx_bytes = render_docx(state)
    html_content = render_html(state)

    assert_zero_drift(docx_bytes, html_content)

    docx_data = extract_docx_data(docx_bytes)
    tab = docx_data["defect_tables"][0]
    assert tab["col_totals"] == ["0.000", "0.000"]
    assert tab["grand_total"] == "0.000"
    assert tab["col_pcts"] == ["0.00", "0.00"]


def test_adversarial_single_cell_table():
    """Single cell table (1 category, 1 row)."""
    state = {
        "metadata": {"number": "ADV-004", "docx_template": "mca-qc-synthetic.docx"},
        "blocks": [
            {
                "id": "tbl_single",
                "type": "table",
                "title": "Single Cell Table",
                "unit": "pcs",
                "grouping_label": "Sample",
                "categories": [{"key": "sound", "label": "Sound"}],
                "rows": [{"group": "Box 1", "values": {"sound": 42}}],
            }
        ],
    }

    docx_bytes = render_docx(state)
    html_content = render_html(state)

    assert_zero_drift(docx_bytes, html_content)

    docx_data = extract_docx_data(docx_bytes)
    tab = docx_data["defect_tables"][0]
    assert tab["row_totals"] == ["42.00"]
    assert tab["row_pcts"] == ["100.00"]
    assert tab["col_totals"] == ["42.00"]
    assert tab["grand_total"] == "42.00"
    assert tab["col_pcts"] == ["100.00"]


def test_adversarial_all_zeros_table_multi_cell():
    """All-zeros table across multiple rows and columns — verifies division by zero safety."""
    state = {
        "metadata": {"number": "ADV-005", "docx_template": "mca-qc-synthetic.docx"},
        "blocks": [
            {
                "id": "tbl_zeros",
                "type": "table",
                "title": "All Zeros Defect Table",
                "unit": "pcs",
                "grouping_label": "Sample",
                "categories": [
                    {"key": "c1", "label": "Defect 1"},
                    {"key": "c2", "label": "Defect 2"},
                    {"key": "c3", "label": "Defect 3"},
                ],
                "rows": [
                    {"group": "Row 1", "values": {"c1": 0, "c2": 0, "c3": 0}},
                    {"group": "Row 2", "values": {"c1": "0", "c2": "0", "c3": "0"}},
                    {"group": "Row 3", "values": {}},  # missing keys default to 0
                ],
            }
        ],
    }

    docx_bytes = render_docx(state)
    html_content = render_html(state)

    assert_zero_drift(docx_bytes, html_content)

    tab = extract_docx_data(docx_bytes)["defect_tables"][0]
    assert tab["row_totals"] == ["0.00", "0.00", "0.00"]
    assert tab["row_pcts"] == [
        "0.00 / 0.00 / 0.00",
        "0.00 / 0.00 / 0.00",
        "0.00 / 0.00 / 0.00",
    ]
    assert tab["col_totals"] == ["0.00", "0.00", "0.00"]
    assert tab["grand_total"] == "0.00"
    assert tab["col_pcts"] == ["0.00", "0.00", "0.00"]


# ===========================================================================
# 2. Extreme Numbers, 3-DP Fractional Weights, and Rounding
# ===========================================================================

def test_adversarial_large_numbers_table():
    """Table with astronomical values (billions / trillions) — verifies no float truncation."""
    state = {
        "metadata": {"number": "ADV-006", "docx_template": "mca-qc-synthetic.docx"},
        "blocks": [
            {
                "id": "tbl_large",
                "type": "table",
                "title": "Large Numbers Cargo Assessment",
                "unit": "pcs",
                "grouping_label": "Vessel Hold",
                "categories": [
                    {"key": "bulk_sound", "label": "Sound Units"},
                    {"key": "bulk_defect", "label": "Damaged Units"},
                ],
                "rows": [
                    {
                        "group": "Hold 1",
                        "values": {
                            "bulk_sound": "500000000000",
                            "bulk_defect": "100000000000",
                        },
                    },
                    {
                        "group": "Hold 2",
                        "values": {
                            "bulk_sound": "400000000000",
                            "bulk_defect": "200000000000",
                        },
                    },
                ],
            }
        ],
    }

    docx_bytes = render_docx(state)
    html_content = render_html(state)

    assert_zero_drift(docx_bytes, html_content)

    tab = extract_docx_data(docx_bytes)["defect_tables"][0]
    assert tab["row_totals"] == ["600000000000.00", "600000000000.00"]
    assert tab["grand_total"] == "1200000000000.00"
    assert tab["col_totals"] == ["900000000000.00", "300000000000.00"]
    assert tab["col_pcts"] == ["75.00", "25.00"]


def test_adversarial_fractional_kg_weights_3dp_rounding():
    """
    Complex fractional weights in kg verifying ROUND_HALF_UP at 3 decimal places
    and 100.00% Hare-Niemeyer balancing.
    """
    state = {
        "metadata": {"number": "ADV-007", "docx_template": "mca-qc-synthetic.docx"},
        "blocks": [
            {
                "id": "tbl_frac_kg",
                "type": "table",
                "title": "Fractional Weight Defect Analysis",
                "unit": "kg",
                "grouping_label": "Pallet",
                "categories": [
                    {"key": "sound", "label": "Sound (kg)"},
                    {"key": "rot", "label": "Rot (kg)"},
                    {"key": "mold", "label": "Mold (kg)"},
                    {"key": "split", "label": "Skin Split (kg)"},
                ],
                "rows": [
                    {
                        "group": "Pallet 1",
                        "values": {
                            "sound": "18.4565",  # rounds to 18.457
                            "rot": "0.1234",     # rounds to 0.123
                            "mold": "0.0456",    # rounds to 0.046
                            "split": "0.0125",   # rounds to 0.013
                        },
                    },
                    {
                        "group": "Pallet 2",
                        "values": {
                            "sound": "22.9999",  # rounds to 23.000
                            "rot": "1.0005",     # rounds to 1.001
                            "mold": "0.5555",    # rounds to 0.556
                            "split": "0.2222",   # rounds to 0.222
                        },
                    },
                ],
            }
        ],
    }

    docx_bytes = render_docx(state)
    html_content = render_html(state)

    assert_zero_drift(docx_bytes, html_content)

    tab = extract_docx_data(docx_bytes)["defect_tables"][0]
    # Pallet 1 sum: 18.4565 + 0.1234 + 0.0456 + 0.0125 = 18.6380 -> 18.638
    # Pallet 2 sum: 22.9999 + 1.0005 + 0.5555 + 0.2222 = 24.7781 -> 24.778
    assert tab["row_totals"] == ["18.638", "24.778"]
    # Col sums:
    # sound: 18.4565 + 22.9999 = 41.4564 -> 41.456
    # rot: 0.1234 + 1.0005 = 1.1239 -> 1.124
    # mold: 0.0456 + 0.5555 = 0.6011 -> 0.601
    # split: 0.0125 + 0.2222 = 0.2347 -> 0.235
    assert tab["col_totals"] == ["41.456", "1.124", "0.601", "0.235"]
    assert tab["grand_total"] == "43.416"
    # Verify percentages sum to exactly 100.00
    pct_sum = sum(Decimal(p) for p in tab["col_pcts"])
    assert pct_sum == Decimal("100.00")


# ===========================================================================
# 3. Hare-Niemeyer Largest Remainder Tie-Breaking Under Adversarial Symmetry
# ===========================================================================

def test_adversarial_hare_niemeyer_3way_tie():
    """3 identical counts: 1/3 each = 33.333...% -> exactly 33.34, 33.33, 33.33 (sum 100.00)."""
    state = {
        "metadata": {"number": "ADV-008", "docx_template": "mca-qc-synthetic.docx"},
        "blocks": [
            {
                "id": "tbl_tie3",
                "type": "table",
                "title": "3-Way Tie Balancing",
                "unit": "pcs",
                "categories": [
                    {"key": "a", "label": "Cat A"},
                    {"key": "b", "label": "Cat B"},
                    {"key": "c", "label": "Cat C"},
                ],
                "rows": [{"group": "Row 1", "values": {"a": 1, "b": 1, "c": 1}}],
            }
        ],
    }

    docx_bytes = render_docx(state)
    html_content = render_html(state)

    assert_zero_drift(docx_bytes, html_content)

    tab = extract_docx_data(docx_bytes)["defect_tables"][0]
    assert tab["col_pcts"] == ["33.34", "33.33", "33.33"]
    assert tab["row_pcts"] == ["33.34 / 33.33 / 33.33"]
    assert sum(Decimal(p) for p in tab["col_pcts"]) == Decimal("100.00")


def test_adversarial_hare_niemeyer_6way_tie():
    """
    6 identical counts: 1/6 each = 16.666...% -> floor=16.66, deficit=4.
    First 4 categories break tie by index -> 16.67, 16.67, 16.67, 16.67, 16.66, 16.66 (sum 100.00).
    """
    categories = [{"key": f"c{i}", "label": f"Cat {i}"} for i in range(1, 7)]
    values = {f"c{i}": 10 for i in range(1, 7)}
    state = {
        "metadata": {"number": "ADV-009", "docx_template": "mca-qc-synthetic.docx"},
        "blocks": [
            {
                "id": "tbl_tie6",
                "type": "table",
                "title": "6-Way Tie Balancing",
                "unit": "pcs",
                "categories": categories,
                "rows": [{"group": "Sample", "values": values}],
            }
        ],
    }

    docx_bytes = render_docx(state)
    html_content = render_html(state)

    assert_zero_drift(docx_bytes, html_content)

    tab = extract_docx_data(docx_bytes)["defect_tables"][0]
    expected_pcts = ["16.67", "16.67", "16.67", "16.67", "16.66", "16.66"]
    assert tab["col_pcts"] == expected_pcts
    assert sum(Decimal(p) for p in tab["col_pcts"]) == Decimal("100.00")


def test_adversarial_hare_niemeyer_7way_tie():
    """
    7 identical counts: 1/7 each = 14.2857...% -> floor=14.28, deficit=4.
    First 4 categories get 14.29, last 3 remain 14.28.
    Total = 4 * 14.29 + 3 * 14.28 = 57.16 + 42.84 = 100.00.
    """
    categories = [{"key": f"c{i}", "label": f"Cat {i}"} for i in range(1, 8)]
    values = {f"c{i}": 5 for i in range(1, 8)}
    state = {
        "metadata": {"number": "ADV-010", "docx_template": "mca-qc-synthetic.docx"},
        "blocks": [
            {
                "id": "tbl_tie7",
                "type": "table",
                "title": "7-Way Tie Balancing",
                "unit": "pcs",
                "categories": categories,
                "rows": [{"group": "Sample", "values": values}],
            }
        ],
    }

    docx_bytes = render_docx(state)
    html_content = render_html(state)

    assert_zero_drift(docx_bytes, html_content)

    tab = extract_docx_data(docx_bytes)["defect_tables"][0]
    expected_pcts = ["14.29", "14.29", "14.29", "14.29", "14.28", "14.28", "14.28"]
    assert tab["col_pcts"] == expected_pcts
    assert sum(Decimal(p) for p in tab["col_pcts"]) == Decimal("100.00")


# ===========================================================================
# 4. Photo Lists: 0 Photos, 1 Photo, 2 Photos, and 100+ Photos Across Groups
# ===========================================================================

def test_adversarial_photo_list_zero_photos():
    """Photo plate with 0 photos (empty groups list)."""
    state = {
        "metadata": {"number": "ADV-011", "docx_template": "mca-qc-synthetic.docx"},
        "blocks": [
            {
                "id": "b_plate_empty",
                "type": "photo_plate",
                "label": "Photographic Evidence",
                "groups": [],
            }
        ],
    }

    docx_bytes = render_docx(state)
    html_content = render_html(state)

    assert_zero_drift(docx_bytes, html_content)

    docx_data = extract_docx_data(docx_bytes)
    html_data = extract_html_data(html_content)

    assert docx_data["photo_captions"] == []
    assert html_data["photo_captions"] == []
    assert any("[No photos in this series]" in p for p in docx_data["paragraphs"])
    assert any("[No photos in this series]" in p for p in html_data["paragraphs"])


def test_adversarial_photo_list_single_photo():
    """Photo plate with exactly 1 photo."""
    state = {
        "metadata": {"number": "ADV-012", "docx_template": "mca-qc-synthetic.docx"},
        "blocks": [
            {
                "id": "b_narr",
                "type": "narrative",
                "additional_text": "Overview of stowage (Photo No. 1).",
            },
            {
                "id": "b_plate_1",
                "type": "photo_plate",
                "label": "Photographic Plate",
                "groups": [
                    {"id": "g1", "observation": "Container front bulkhead", "asset_ids": ["a1"]}
                ],
            },
        ],
    }

    docx_bytes = render_docx(state)
    html_content = render_html(state)

    assert_zero_drift(docx_bytes, html_content)

    docx_data = extract_docx_data(docx_bytes)
    html_data = extract_html_data(html_content)

    expected_caption = ["Photo No. 1 — Container front bulkhead"]
    assert docx_data["photo_captions"] == expected_caption
    assert html_data["photo_captions"] == expected_caption
    assert docx_data["photo_ranges"] == ["(Photo No. 1)"]
    assert html_data["photo_ranges"] == ["(Photo No. 1)"]


def test_adversarial_photo_list_two_photos_pair_and_separate():
    """Two photos in single group (pair) and in separate groups."""
    # Subcase A: Pair in 1 group -> (Photo Nos. 1 & 2)
    state_pair = {
        "metadata": {"number": "ADV-013A", "docx_template": "mca-qc-synthetic.docx"},
        "blocks": [
            {
                "id": "b_narr",
                "type": "narrative",
                "additional_text": "Security seals verified (Photo Nos. 1 & 2).",
            },
            {
                "id": "b_plate_pair",
                "type": "photo_plate",
                "label": "Photographic Evidence",
                "groups": [
                    {"id": "g1", "observation": "Bolt seal verification", "asset_ids": ["p1", "p2"]}
                ],
            },
        ],
    }

    docx_pair = render_docx(state_pair)
    html_pair = render_html(state_pair)

    assert_zero_drift(docx_pair, html_pair)
    assert extract_docx_data(docx_pair)["photo_ranges"] == ["(Photo Nos. 1 & 2)"]

    # Subcase B: 2 separate groups of 1 photo -> (Photo No. 1) and (Photo No. 2)
    state_sep = {
        "metadata": {"number": "ADV-013B", "docx_template": "mca-qc-synthetic.docx"},
        "blocks": [
            {
                "id": "b_narr",
                "type": "narrative",
                "additional_text": "Left door (Photo No. 1) and right door (Photo No. 2).",
            },
            {
                "id": "b_plate_sep",
                "type": "photo_plate",
                "label": "Photographic Evidence",
                "groups": [
                    {"id": "g1", "observation": "Left door seal", "asset_ids": ["p1"]},
                    {"id": "g2", "observation": "Right door handle", "asset_ids": ["p2"]},
                ],
            },
        ],
    }

    docx_sep = render_docx(state_sep)
    html_sep = render_html(state_sep)

    assert_zero_drift(docx_sep, html_sep)
    assert extract_docx_data(docx_sep)["photo_ranges"] == ["(Photo No. 1)", "(Photo No. 2)"]


def test_adversarial_photo_list_100_plus_photos_stress():
    """
    Stress test with 120 photos across 10 observation groups.
    Mix of singles (count 1), pairs (count 2), and ranges (count 3..25).
    Verifies that all 120 captions, range strings, and table cells match bit-for-bit.
    """
    group_specs = [
        ("g1", "Exterior container seals", 2),       # Photos 1-2 (pair)
        ("g2", "Temperature recorder display", 1),   # Photo 3 (single)
        ("g3", "Top tier box condensation", 15),     # Photos 4-18 (range)
        ("g4", "Bottom pallet corner collapse", 25), # Photos 19-43 (range)
        ("g5", "Pulp temperature probe checks", 2),  # Photos 44-45 (pair)
        ("g6", "Fruit internal rot samples", 30),    # Photos 46-75 (range)
        ("g7", "Packaging label compliance", 1),    # Photo 76 (single)
        ("g8", "Ventilation flap settings", 4),      # Photos 77-80 (range)
        ("g9", "Floor drain obstruction", 20),      # Photos 81-100 (range)
        ("g10", "Final post-restow inspection", 20), # Photos 101-120 (range)
    ]

    total_photos_count = sum(spec[2] for spec in group_specs)
    assert total_photos_count == 120

    groups = []
    photo_narrative_snippets = []
    for gid, obs, count in group_specs:
        asset_ids = [f"asset_{gid}_{i}" for i in range(1, count + 1)]
        groups.append({"id": gid, "observation": obs, "asset_ids": asset_ids})

    computed_ranges = compute_photo_ranges(groups)
    assert computed_ranges["total_photos"] == 120

    for gid, obs, count in group_specs:
        lbl = computed_ranges["groups"][gid]["label"]
        photo_narrative_snippets.append(f"{obs} {lbl}")

    narrative_text = "Inspection log: " + "; ".join(photo_narrative_snippets) + "."

    state = {
        "metadata": {"number": "ADV-014-STRESS", "docx_template": "mca-qc-synthetic.docx"},
        "blocks": [
            {
                "id": "b_narr",
                "type": "narrative",
                "section": "EXTENSIVE PHOTO EVIDENCE",
                "additional_text": narrative_text,
            },
            {
                "id": "b_plate_120",
                "type": "photo_plate",
                "label": "Comprehensive Survey Plate",
                "groups": groups,
            },
        ],
    }

    docx_bytes = render_docx(state)
    html_content = render_html(state)

    assert_zero_drift(docx_bytes, html_content)

    docx_data = extract_docx_data(docx_bytes)
    html_data = extract_html_data(html_content)

    # Assert exactly 120 captions
    assert len(docx_data["photo_captions"]) == 120
    assert len(html_data["photo_captions"]) == 120
    assert docx_data["photo_captions"] == html_data["photo_captions"]

    # Verify first, middle, and last captions
    assert docx_data["photo_captions"][0] == "Photo No. 1 — Exterior container seals"
    assert docx_data["photo_captions"][75] == "Photo No. 76 — Packaging label compliance"
    assert docx_data["photo_captions"][-1] == "Photo No. 120 — Final post-restow inspection"

    # Verify all 10 range references matched in narrative
    assert len(docx_data["photo_ranges"]) == 10
    assert docx_data["photo_ranges"] == html_data["photo_ranges"]
    assert "(Photo Nos. 1 & 2)" in docx_data["photo_ranges"]
    assert "(Photo No. 3)" in docx_data["photo_ranges"]
    assert "(Photo Nos. 4 to 18)" in docx_data["photo_ranges"]
    assert "(Photo Nos. 101 to 120)" in docx_data["photo_ranges"]


def test_adversarial_multiple_photo_plates_contiguous_numbering():
    """
    Multiple photo plates across the document — verifies that photo numbering
    advances contiguously without resets across plate blocks.
    Plate 1: 10 photos (1-10)
    Plate 2: 15 photos (11-25)
    """
    state = {
        "metadata": {"number": "ADV-015", "docx_template": "mca-qc-synthetic.docx"},
        "blocks": [
            {
                "id": "b_plate_1",
                "type": "photo_plate",
                "label": "Plate 1 - Unloading",
                "groups": [
                    {"id": "g1_1", "observation": "Container arrival", "asset_ids": [f"a_{i}" for i in range(1, 11)]}
                ],
            },
            {
                "id": "b_plate_2",
                "type": "photo_plate",
                "label": "Plate 2 - Sorting",
                "groups": [
                    {"id": "g2_1", "observation": "Cold store sorting", "asset_ids": [f"b_{i}" for i in range(1, 16)]}
                ],
            },
        ],
    }

    docx_bytes = render_docx(state)
    html_content = render_html(state)

    assert_zero_drift(docx_bytes, html_content)

    docx_data = extract_docx_data(docx_bytes)
    assert len(docx_data["photo_captions"]) == 25
    assert docx_data["photo_captions"][0] == "Photo No. 1 — Container arrival"
    assert docx_data["photo_captions"][9] == "Photo No. 10 — Container arrival"
    assert docx_data["photo_captions"][10] == "Photo No. 11 — Cold store sorting"
    assert docx_data["photo_captions"][24] == "Photo No. 25 — Cold store sorting"


# ===========================================================================
# 5. Special Characters, Escaping, and Unicode Resilience
# ===========================================================================

def test_adversarial_special_characters_and_markup_resilience():
    """Verifies that XML and HTML special characters (<, >, &, \", ') do not corrupt or drift."""
    state = {
        "metadata": {"number": "ADV-016", "docx_template": "mca-qc-synthetic.docx"},
        "blocks": [
            {
                "id": "b_part",
                "type": "particulars",
                "section": "CARGO & VESSEL DETAILS",
                "rows": [
                    {"label": "Vessel & Voyage", "value": ["M/V 'OCEAN STAR' <V.42A> & CO."]},
                    {"label": "Invoice & Claim", "value": [{"currency": "EUR", "amount": "95,000.50"}]},
                ],
            },
            {
                "id": "b_tbl",
                "type": "table",
                "title": "Grade <A> & Defect (B&C) Analysis",
                "unit": "pcs",
                "grouping_label": "Lot <#1> & #2",
                "categories": [
                    {"key": "cat_a", "label": "Sound & Fresh <Grade 1>"},
                    {"key": "cat_b", "label": "Blemishes & Scars > 5mm"},
                ],
                "rows": [
                    {"group": "Batch A & B", "values": {"cat_a": 50, "cat_b": 25}},
                ],
            },
            {
                "id": "b_plate",
                "type": "photo_plate",
                "label": "Evidence & Scans",
                "groups": [
                    {"id": "g1", "observation": "Fruit cut & internal core <mold>", "asset_ids": ["img1"]},
                ],
            },
        ],
    }

    docx_bytes = render_docx(state)
    html_content = render_html(state)

    assert_zero_drift(docx_bytes, html_content)

    docx_data = extract_docx_data(docx_bytes)
    html_data = extract_html_data(html_content)

    assert "Photo No. 1 — Fruit cut & internal core <mold>" in docx_data["photo_captions"]
    assert "Photo No. 1 — Fruit cut & internal core <mold>" in html_data["photo_captions"]
    assert docx_data["defect_tables"][0]["full_grid"] == html_data["defect_tables"][0]["full_grid"]


# ===========================================================================
# 6. Empirical Probes: Invariant Assertions and Failure Modes
# ===========================================================================

def test_adversarial_empty_asset_id_group_raises_assertion():
    """
    Verifies that backend compute_photo_ranges enforces Master Spec §10.2:
    Every photo group must contain at least one photo (empty group raises AssertionError).
    """
    empty_group_state = {
        "metadata": {"number": "ADV-017", "docx_template": "mca-qc-synthetic.docx"},
        "blocks": [
            {
                "id": "b_plate",
                "type": "photo_plate",
                "groups": [
                    {"id": "g_empty", "observation": "Empty group", "asset_ids": []}
                ],
            }
        ],
    }

    with pytest.raises(AssertionError) as excinfo:
        compute(empty_group_state)
    assert "Every group must contain at least one photo" in str(excinfo.value)


def test_adversarial_duplicate_asset_id_across_groups_raises_assertion():
    """
    Verifies that backend compute_photo_ranges enforces Master Spec §10.2:
    Each photo must belong to exactly one group (duplicate asset_id raises AssertionError).
    """
    duplicate_asset_state = {
        "metadata": {"number": "ADV-018", "docx_template": "mca-qc-synthetic.docx"},
        "blocks": [
            {
                "id": "b_plate",
                "type": "photo_plate",
                "groups": [
                    {"id": "g1", "observation": "First plate", "asset_ids": ["photo_dup"]},
                    {"id": "g2", "observation": "Second plate", "asset_ids": ["photo_dup"]},
                ],
            }
        ],
    }

    with pytest.raises(AssertionError) as excinfo:
        compute(duplicate_asset_state)
    assert "Each photo must belong to exactly one group" in str(excinfo.value)


def test_adversarial_float_rejection_in_compute():
    """
    Verifies that passing Python float into table values raises TypeError
    per CRITICAL-RULES §1 (Decimal only, never float).
    """
    float_state = {
        "blocks": [
            {
                "type": "table",
                "categories": [{"key": "sound", "label": "Sound"}],
                "rows": [{"group": "Box 1", "values": {"sound": 12.34}}],  # float
            }
        ]
    }

    with pytest.raises(TypeError) as excinfo:
        compute(float_state)
    assert "Never pass float" in str(excinfo.value)
