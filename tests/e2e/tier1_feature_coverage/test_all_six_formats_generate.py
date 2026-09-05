"""
Automated Verification: All Six Report Formats Generate Correctly.
Master Spec §8, §14 (Day 14).

Tests both DOCX and HTML generation for all six canonical templates:
1. general_cargo_sea_survey
2. general_cargo_air_survey
3. perishable_sea_survey
4. perishable_air_survey
5. perishable_qc_sea
6. perishable_qc_air
"""

import pytest
from app.seeds.templates import SIX_CANONICAL_TEMPLATES
from app.render.docx.engine import render_docx
from app.render.html.engine import render_html


def _build_sample_state_for_template(template: dict) -> dict:
    """Creates a populated Block State corresponding to the template's block_sequence."""
    tmpl_id = template["id"]
    family = template["family"]
    mode = template["mode"]

    carriage_units = [
        {"id": "u1", "unit_type": "CONTAINER" if mode == "SEA" else "ULD", "identifier": "MSKU1234567" if mode == "SEA" else "AKE12345AA"}
    ]

    blocks = []
    for b_def in template["block_sequence"]:
        btype = b_def.get("type")
        bid = b_def.get("id", f"b_{btype}")

        if btype == "parties":
            blocks.append({
                "id": bid,
                "type": "parties",
                "rows": [
                    {"role": "Insurers", "name": "Oceanic Underwriters Ltd"},
                    {"role": "Consignee", "name": "Global Cargo Imports Pvt Ltd"},
                ],
            })
        elif btype == "attendance":
            blocks.append({
                "id": bid,
                "type": "attendance",
                "rows": [
                    {"name": "Mr. K. Sharma", "designation": "Cargo Surveyor", "representing": "Marine Cargo Agencies"},
                ],
            })
        elif btype == "particulars":
            blocks.append({
                "id": bid,
                "type": "particulars",
                "rows": [
                    {"label": "Vessel / Flight", "value": ["OCEANIC VOYAGER" if mode == "SEA" else "AI-101"]},
                    {"label": "Document No", "value": ["BL-992817" if mode == "SEA" else "098-12345675"]},
                ],
            })
        elif btype == "timeline":
            blocks.append({
                "id": bid,
                "type": "timeline",
                "rows": [
                    {"event": "ARRIVAL", "date": "2026-08-10", "location": "Port / Airport"},
                    {"event": "SURVEY", "date": "2026-08-12", "location": "Warehouse"},
                ],
            })
        elif btype == "narrative":
            blocks.append({
                "id": bid,
                "type": "narrative",
                "section": b_def.get("section", "NARRATIVE SECTION"),
                "additional_text": "Survey conducted in presence of representatives with no exceptions noted.",
            })
        elif btype == "measurements":
            blocks.append({
                "id": bid,
                "type": "measurements",
                "rows": [
                    {"subject": "cargo temperature", "min": "2.0", "max": "4.0", "unit": "C"},
                ],
            })
        elif btype == "table":
            blocks.append({
                "id": bid,
                "type": "table",
                "unit": "pcs",
                "categories": [{"key": "sound", "label": "Sound"}, {"key": "defect", "label": "Defect"}],
                "rows": [{"group": "Sample Lot", "values": {"sound": 100, "defect": 5}}],
            })
        elif btype == "reconciliation":
            blocks.append({
                "id": bid,
                "type": "reconciliation",
                "formula": "GROSS_MINUS_CONTAINER_TARE",
                "rows": [
                    {"subject": "Unit 1", "gross": "12000", "container_tare": "2000", "reference": "10000"},
                ],
            })
        elif btype == "inventory":
            blocks.append({
                "id": bid,
                "type": "inventory",
                "packages": [
                    {
                        "package_no": "P-1",
                        "package_type": "CRATE",
                        "contents": "Compressor Assembly",
                        "parts": [{"part_no": "CMP-1", "description": "Housing", "quantity": 1, "damages": [{"description": "Fractured base"}]}],
                    }
                ],
            })
        elif btype == "unit_group":
            blocks.append({
                "id": bid,
                "type": "unit_group",
                "repeat_for": "carriage_units",
                "heading_template": "{index}) UNIT {identifier}: (SEE {photo_ref})",
                "blocks": [
                    {
                        "id": "ub_table",
                        "type": "table",
                        "unit": "pcs",
                        "categories": [{"key": "sound", "label": "Sound"}],
                        "rows": [{"group": "Lot A", "values": {"sound": 50}}],
                    }
                ],
            })
        elif btype == "photo_plate":
            blocks.append({
                "id": bid,
                "type": "photo_plate",
                "series_id": "survey",
                "groups": [{"id": "g1", "observation": "Inspection view", "asset_ids": ["a1"]}],
            })
        elif btype == "annexures":
            blocks.append({
                "id": bid,
                "type": "annexures",
                "rows": [{"prefix": "A", "title": "Inspection Certificate", "asset_id": "a10"}],
            })
        elif btype == "fixed_text":
            blocks.append({
                "id": bid,
                "type": "fixed_text",
                "content": "Issued without prejudice, subject to terms of carriage.",
            })

    return {
        "metadata": {
            "number": f"M-SAMPLE-{tmpl_id.upper()}",
            "family": family,
            "template_id": tmpl_id,
            "docx_template": "mca-synthetic-v1.docx",
        },
        "transport": {
            "mode": mode,
            "document": {
                "kind": "BILL_OF_LADING" if mode == "SEA" else "AIR_WAYBILL",
                "number": "DOC12345",
            },
        },
        "carriage_units": carriage_units,
        "blocks": blocks,
        "assets": {
            "a1": {"kind": "photo", "original_path": "photos/p1.jpg"},
        },
    }


@pytest.mark.parametrize("template", SIX_CANONICAL_TEMPLATES[:6])
def test_each_canonical_format_generates_docx_and_html(template):
    """Assert that every one of the six canonical report formats renders to DOCX and HTML without error."""
    state = _build_sample_state_for_template(template)

    # 1. DOCX Generation
    docx_bytes = render_docx(state)
    assert docx_bytes is not None
    assert len(docx_bytes) > 500  # Non-empty valid DOCX file

    # 2. HTML Preview Generation
    html_output = render_html(state)
    assert html_output is not None
    assert len(html_output) > 200
    assert "MARINE CARGO AGENCIES" in html_output
    assert state["metadata"]["number"] in html_output
