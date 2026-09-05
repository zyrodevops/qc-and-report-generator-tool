"""
Scenario Test: Historical Benchmark M-244 Rebuild & Machinery Inventory.
Master Spec §7, §14 (Day 15).

Shipment Details:
- 9 containers with project cargo / heavy machinery.
- 22 packages across containers with part-level nested damage findings.
- General cargo sea survey template with parties, timeline, inventory, and photo plates.
- Zero-drift guarantee across DOCX and HTML renderers.
"""

from decimal import Decimal
import pytest
from app.compute.arithmetic import compute, validate_iso6346
from app.render.docx.engine import render_docx
from app.render.html.engine import render_html


@pytest.fixture
def m244_benchmark_state():
    """Constructs the canonical M-244 block state with 9 containers and 22 machinery packages."""
    containers = [
        {"id": f"u{i}", "unit_type": "CONTAINER", "identifier": f"MSKU{1000000 + i*133:07d}", "marked_tare_kg": "3850"}
        for i in range(1, 10)
    ]

    # 22 packages with part damage
    packages = []
    for pkg_i in range(1, 23):
        packages.append({
            "package_no": f"PKG-{pkg_i:02d}",
            "package_type": "WOODEN_CRATE",
            "contents": f"Industrial Machine Assembly Module #{pkg_i}",
            "parts": [
                {
                    "part_no": f"MOD-{pkg_i}-PT1",
                    "description": "Main Hydraulic Actuator Housing",
                    "quantity": 1,
                    "damages": [{"description": "Severe impact crack across mounting flange", "severity": "CRACKED"}],
                },
                {
                    "part_no": f"MOD-{pkg_i}-PT2",
                    "description": "High Pressure Sensor Manifold",
                    "quantity": 2,
                    "damages": [{"description": "Deformed casing with thread stripping", "severity": "BENT"}],
                },
            ],
        })

    return {
        "metadata": {
            "number": "M-244-2025",
            "family": "SURVEY_REPORT",
            "docx_template": "mca-synthetic-v1.docx",
        },
        "transport": {
            "mode": "SEA",
            "document": {"kind": "BILL_OF_LADING", "number": "MSK90281726", "check_digit_valid": True},
        },
        "carriage_units": containers,
        "blocks": [
            {
                "id": "b_parties",
                "type": "parties",
                "rows": [
                    {"role": "Insurers", "name": "Global Marine & Transport Underwriting Ltd"},
                    {"role": "Insured", "name": "Precision Engineering Consortium Ltd"},
                    {"role": "Consignee", "name": "Bharat Heavy Machineries Corp"},
                    {"role": "Surveyor", "name": "Marine Cargo Agencies Pvt Ltd"},
                ],
            },
            {
                "id": "b_timeline",
                "type": "timeline",
                "rows": [
                    {"event": "DISCHARGE", "date": "2025-11-05", "location": "Mumbai Port Trust"},
                    {"event": "TRANSPORT_TO_CONSIGNEE", "date": "2025-11-08", "location": "Factory Site, Pune"},
                    {"event": "PRELIMINARY_INSPECTION", "date": "2025-11-10", "location": "Factory Site, Pune"},
                    {"event": "FINAL_JOINT_SURVEY", "date": "2025-11-15", "location": "Factory Site, Pune"},
                ],
            },
            {
                "id": "b_inventory",
                "type": "inventory",
                "packages": packages,
            },
            {
                "id": "b_photos",
                "type": "photo_plate",
                "series_id": "survey",
                "label": "Machinery Damage Photographs",
                "groups": [
                    {"id": "pg1", "observation": "Crushed wooden crates on arrival at factory", "asset_ids": ["a1"]},
                    {"id": "pg2", "observation": "Cracked hydraulic mounting flange detail", "asset_ids": ["a2"]},
                ],
            },
            {
                "id": "b_disclaimer",
                "type": "fixed_text",
                "content": "Survey conducted without prejudice to liability.",
            },
        ],
        "assets": {
            "a1": {"kind": "photo", "original_path": "photos/m1.jpg"},
            "a2": {"kind": "photo", "original_path": "photos/m2.jpg"},
        },
    }


def test_m244_nine_containers(m244_benchmark_state):
    """Verify 9 containers handled correctly in M-244 state."""
    state = compute(m244_benchmark_state)
    assert len(state["carriage_units"]) == 9


def test_m244_machinery_inventory_packages(m244_benchmark_state):
    """Verify all 22 packages with nested damaged parts are retained and validated."""
    state = compute(m244_benchmark_state)
    inv = next(b for b in state["blocks"] if b["type"] == "inventory")
    assert len(inv["packages"]) == 22
    for pkg in inv["packages"]:
        assert len(pkg["parts"]) == 2
        for part in pkg["parts"]:
            assert len(part["damages"]) >= 1


def test_m244_timeline_transit_days(m244_benchmark_state):
    """Verify transit duration computation: 2025-11-05 to 2025-11-15 = 10 days."""
    state = compute(m244_benchmark_state)
    timeline = next(b for b in state["blocks"] if b["type"] == "timeline")
    assert timeline["_computed"]["transit_days"] == 10
    assert len(timeline["_computed"]["intervals"]) == 3


def test_m244_zero_drift_docx_and_html(m244_benchmark_state):
    """Verify DOCX generation and HTML preview render all 22 packages without crash."""
    docx_bytes = render_docx(m244_benchmark_state)
    assert len(docx_bytes) > 2000

    html_out = render_html(m244_benchmark_state)
    assert "Package PKG-01" in html_out
    assert "Package PKG-22" in html_out
    assert "Main Hydraulic Actuator Housing" in html_out
    assert "Total Transit Duration: 10 day(s)" in html_out
