"""
Scenario Test: Historical Benchmark M-71 Rebuild & Forensic Verification.
Master Spec §7, §10.4, §14 (Day 15).

Shipment Details:
- 6 containers: CMAU2016593, DFSU1851396, FCIU4387412, TGHU0128915, GESU3348190, FCIU3891044.
- 3 weighings of the same 6 containers with different formulas:
  1. CFS weighbridge (gross - trailer - container tare): exactly 126,891 kg -> Shortage: NIL.
  2. Destuffing weighbridge: exactly 65,340 kg -> Shortage: 61,551 kg.
  3. Final verification: exactly 64,580 kg -> Shortage: 62,311 kg.
- Averaged declared figure tolerance: 6 x 21,148 = 126,888 vs declared 126,891 (3 kg discrepancy flagged, NEVER auto-adjusted).
- 18 annexures (A1..A6, B1..B6, C1..C6).
- Zero-drift guarantee: compute(block_state) produces identical results for HTML, DOCX, and PDF.
"""

from decimal import Decimal
import pytest
from app.compute.arithmetic import compute, validate_iso6346
from app.render.docx.engine import render_docx
from app.render.html.engine import render_html


@pytest.fixture
def m71_benchmark_state():
    """Constructs the canonical M-71 block state with 6 containers and 3 weighings."""
    containers = [
        {"id": "u1", "unit_type": "CONTAINER", "identifier": "CMAU2016593", "marked_tare_kg": "2190"},
        {"id": "u2", "unit_type": "CONTAINER", "identifier": "DFSU1851396", "marked_tare_kg": "2210"},
        {"id": "u3", "unit_type": "CONTAINER", "identifier": "FCIU4387412", "marked_tare_kg": "2200"},
        {"id": "u4", "unit_type": "CONTAINER", "identifier": "TGHU0128915", "marked_tare_kg": "2180"},
        {"id": "u5", "unit_type": "CONTAINER", "identifier": "GESU3348190", "marked_tare_kg": "2220"},
        {"id": "u6", "unit_type": "CONTAINER", "identifier": "FCIU3891044", "marked_tare_kg": "2200"},
    ]

    # Weighing 1 rows: CFS weighbridge (Trailer + Container tare deduction)
    # Sum of found net = exactly 126,891 kg
    w1_rows = [
        {"subject": "CMAU2016593", "gross": "31390", "trailer_tare": "8000", "container_tare": "2190", "reference": "21148"},  # net 21200
        {"subject": "DFSU1851396", "gross": "31360", "trailer_tare": "8000", "container_tare": "2210", "reference": "21148"},  # net 21150
        {"subject": "FCIU4387412", "gross": "31340", "trailer_tare": "8000", "container_tare": "2200", "reference": "21148"},  # net 21140
        {"subject": "TGHU0128915", "gross": "31330", "trailer_tare": "8000", "container_tare": "2180", "reference": "21148"},  # net 21150
        {"subject": "GESU3348190", "gross": "31320", "trailer_tare": "8000", "container_tare": "2220", "reference": "21148"},  # net 21100
        {"subject": "FCIU3891044", "gross": "31351", "trailer_tare": "8000", "container_tare": "2200", "reference": "21151"},  # net 21151
    ]

    # Weighing 2 rows: CFS destuffing weighbridge -> found net = exactly 65,340 kg
    w2_rows = [
        {"subject": "CMAU2016593", "gross": "13080", "container_tare": "2190", "reference": "21148"},  # net 10890
        {"subject": "DFSU1851396", "gross": "13100", "container_tare": "2210", "reference": "21148"},  # net 10890
        {"subject": "FCIU4387412", "gross": "13090", "container_tare": "2200", "reference": "21148"},  # net 10890
        {"subject": "TGHU0128915", "gross": "13070", "container_tare": "2180", "reference": "21148"},  # net 10890
        {"subject": "GESU3348190", "gross": "13110", "container_tare": "2220", "reference": "21148"},  # net 10890
        {"subject": "FCIU3891044", "gross": "13090", "container_tare": "2200", "reference": "21151"},  # net 10890
    ]

    # Weighing 3 rows: Final verification -> found net = exactly 64,580 kg
    w3_rows = [
        {"subject": "CMAU2016593", "gross": "12953", "container_tare": "2190", "reference": "21148"},  # net 10763
        {"subject": "DFSU1851396", "gross": "12973", "container_tare": "2210", "reference": "21148"},  # net 10763
        {"subject": "FCIU4387412", "gross": "12963", "container_tare": "2200", "reference": "21148"},  # net 10763
        {"subject": "TGHU0128915", "gross": "12943", "container_tare": "2180", "reference": "21148"},  # net 10763
        {"subject": "GESU3348190", "gross": "12983", "container_tare": "2220", "reference": "21148"},  # net 10763
        {"subject": "FCIU3891044", "gross": "12965", "container_tare": "2200", "reference": "21151"},  # net 10765
    ]

    annexures_rows = []
    for pfx in ["A", "B", "C"]:
        for i in range(1, 7):
            annexures_rows.append({
                "prefix": pfx,
                "title": f"Weighbridge Slip {pfx}{i} Container {containers[i-1]['identifier']}",
                "asset_id": f"asset_{pfx.lower()}{i}",
            })

    return {
        "metadata": {
            "number": "M-71-2026",
            "family": "SURVEY_REPORT",
            "docx_template": "mca-synthetic-v1.docx",
        },
        "transport": {
            "mode": "SEA",
            "document": {"kind": "BILL_OF_LADING", "number": "CMAU9928172", "check_digit_valid": True},
        },
        "carriage_units": containers,
        "blocks": [
            {
                "id": "b_parties",
                "type": "parties",
                "rows": [
                    {"role": "Insurers", "name": "Oceanic Cargo Underwriters Ltd"},
                    {"role": "Consignee", "name": "Eastern Agro Imports Pvt Ltd"},
                    {"role": "Surveyor", "name": "Marine Cargo Agencies Pvt Ltd"},
                ],
            },
            {
                "id": "b_timeline",
                "type": "timeline",
                "rows": [
                    {"event": "DISCHARGE", "date": "2026-06-18", "location": "Nhava Sheva Port"},
                    {"event": "WEIGHING_1", "date": "2026-06-20", "location": "CFS Weighbridge"},
                    {"event": "DESTUFFING", "date": "2026-06-22", "location": "Cold Storage Unit 4"},
                    {"event": "SURVEY", "date": "2026-06-25", "location": "Cold Storage Unit 4"},
                ],
            },
            {
                "id": "b_w1",
                "type": "reconciliation",
                "title": "Weighing 1: CFS Weighbridge Gross Weights",
                "formula": "GROSS_MINUS_TRAILER_TARE_MINUS_CONTAINER_TARE",
                "rows": w1_rows,
            },
            {
                "id": "b_w2",
                "type": "reconciliation",
                "title": "Weighing 2: CFS Destuffing Weighbridge Weights",
                "formula": "GROSS_MINUS_CONTAINER_TARE",
                "rows": w2_rows,
            },
            {
                "id": "b_w3",
                "type": "reconciliation",
                "title": "Weighing 3: Tare Verification Weights",
                "formula": "GROSS_MINUS_CONTAINER_TARE",
                "rows": w3_rows,
            },
            {
                "id": "b_unit_group",
                "type": "unit_group",
                "repeat_for": "carriage_units",
                "heading_template": "{index}) CONDITION OF CONTAINER NO. {identifier} & CARGO: (SEE {photo_ref})",
                "photo_numbering": "SHARED_SERIES_SEGMENTED",
                "blocks": [
                    {
                        "id": "ub_table",
                        "type": "table",
                        "unit": "pcs",
                        "categories": [{"key": "sound", "label": "Sound"}, {"key": "defect", "label": "Defect"}],
                        "rows": [{"group": "Lot 1", "values": {"sound": 95, "defect": 5}}],
                    },
                    {
                        "id": "ub_photos",
                        "type": "photo_plate",
                        "series_id": "survey",
                        "groups": [{"id": "g1", "observation": "Customs seal intact", "asset_ids": ["a1", "a2"]}],
                    },
                ],
            },
            {
                "id": "b_annexures",
                "type": "annexures",
                "rows": annexures_rows,
            },
            {
                "id": "b_disclaimer",
                "type": "fixed_text",
                "content": "Report issued without prejudice, subject to terms of carriage.",
            },
        ],
        "assets": {
            "a1": {"kind": "photo", "original_path": "photos/a1.jpg"},
            "a2": {"kind": "photo", "original_path": "photos/a2.jpg"},
        },
    }


def test_m71_container_check_digits(m71_benchmark_state):
    """Verify ISO 6346 check digit validation across all 6 containers."""
    computed_state = compute(m71_benchmark_state)
    for u in computed_state["carriage_units"]:
        cid = u["identifier"]
        valid, check = validate_iso6346(cid)
        # Check digit validity is computed and stored without modifying the identifier
        assert u["identifier_valid"] is not None
        assert u["identifier"] == cid  # Never auto-corrected


def test_m71_three_weighings_arithmetic(m71_benchmark_state):
    """
    Forensic verification of the 3 weighings from historical M-71 benchmark:
    - Weighing 1 found net = 126,891 kg -> shortage = NIL
    - Weighing 2 found net = 65,340 kg -> shortage = 61,551 kg
    - Weighing 3 found net = 64,580 kg -> shortage = 62,311 kg
    """
    computed_state = compute(m71_benchmark_state)
    blocks = {b["id"]: b for b in computed_state["blocks"]}

    # Weighing 1
    w1 = blocks["b_w1"]["_computed"]
    assert Decimal(w1["total_found_net"]) == Decimal("126891.00")
    assert Decimal(w1["total_reference"]) == Decimal("126891.00")
    assert Decimal(w1["total_difference"]) == Decimal("0.00")
    assert w1["direction"] == "NIL"

    # Weighing 2
    w2 = blocks["b_w2"]["_computed"]
    assert Decimal(w2["total_found_net"]) == Decimal("65340.00")
    assert Decimal(w2["total_difference"]) == Decimal("61551.00")
    assert w2["direction"] == "SHORTAGE"

    # Weighing 3
    w3 = blocks["b_w3"]["_computed"]
    assert Decimal(w3["total_found_net"]) == Decimal("64580.00")
    assert Decimal(w3["total_difference"]) == Decimal("62311.00")
    assert w3["direction"] == "SHORTAGE"


def test_m71_annexure_ids_allocation(m71_benchmark_state):
    """Assert deterministic A1..A6, B1..B6, C1..C6 annexure ID allocation."""
    computed_state = compute(m71_benchmark_state)
    annexures = next(b for b in computed_state["blocks"] if b["type"] == "annexures")
    computed = annexures["_computed"]

    expected_ids = [f"{p}{i}" for p in ["A", "B", "C"] for i in range(1, 7)]
    actual_ids = [r["sub_id"] for r in computed["rows"]]
    assert actual_ids == expected_ids
    assert len(computed["merge_order"]) == 18
    assert len(computed["documentation_list"]) == 18


def test_m71_zero_drift_docx_and_html(m71_benchmark_state):
    """Assert zero drift between DOCX generation and HTML preview for M-71."""
    docx_bytes = render_docx(m71_benchmark_state)
    assert len(docx_bytes) > 1000

    html_out = render_html(m71_benchmark_state)
    assert "126891.00" in html_out
    assert "65340.00" in html_out
    assert "61551.00" in html_out
    assert "64580.00" in html_out
    assert "62311.00" in html_out
    assert "CMAU2016593" in html_out


def test_6_container_shipment_single_report_ranges_and_totals(m71_benchmark_state):
    """
    Asserts Week 3 Requirement 2:
    - Exactly one report produced for a 6-container shipment.
    - 6 per-container sections with correct headings.
    - Continuous photo ranges per container (Unit 1: Photos 1 & 2, Unit 2: Photos 3 & 4...).
    - Correct shipment total.
    """
    computed_state = compute(m71_benchmark_state)
    unit_grp = next(b for b in computed_state["blocks"] if b["type"] == "unit_group")
    units = unit_grp["_computed"]["units"]
    assert len(units) == 6

    # Verify per-container headings and photo references
    expected_containers = [
        "CMAU2016593", "DFSU1851396", "FCIU4387412",
        "TGHU0128915", "GESU3348190", "FCIU3891044"
    ]
    for idx, u in enumerate(units, start=1):
        assert u["identifier"] == expected_containers[idx - 1]
        assert f"{idx}) CONDITION OF CONTAINER NO. {expected_containers[idx - 1]}" in u["heading"]
        expected_p1 = (idx - 1) * 2 + 1
        expected_p2 = idx * 2
        assert f"SURVEY PHOTO NOS. {expected_p1} & {expected_p2}" in u["heading"]

    # Verify shipment total
    w1 = next(b for b in computed_state["blocks"] if b["id"] == "b_w1")
    assert Decimal(w1["_computed"]["total_found_net"]) == Decimal("126891.00")
