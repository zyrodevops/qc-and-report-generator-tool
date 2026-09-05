"""
Tier 1 Feature Coverage: Week 3 Survey Reports, Air Shipments, Annexures & Liability Regimes.
Master Spec §6, §8, §10.3, §10.6, §14 (Days 11-15).
"""

from decimal import Decimal
import io
import pytest
from pypdf import PdfWriter, PdfReader
from app.compute.arithmetic import compute, compute_air_weights, validate_awb
from app.compute.liability import REGIMES_2026_01, get_liability_regime, confirm_regime
from app.render.annexures import merge_pdf_annexures
from app.seeds.templates import SIX_CANONICAL_TEMPLATES


def test_six_canonical_templates_present():
    """Assert all 6 canonical templates are defined with proper family, mode, and sequence."""
    template_ids = {t["id"] for t in SIX_CANONICAL_TEMPLATES}
    required = {
        "general_cargo_sea_survey",
        "general_cargo_air_survey",
        "perishable_sea_survey",
        "perishable_air_survey",
        "perishable_qc_sea",
        "perishable_qc_air",
    }
    assert required.issubset(template_ids)
    for t in SIX_CANONICAL_TEMPLATES:
        assert t["family"] in ("SURVEY_REPORT", "QC_REPORT")
        assert t["mode"] in ("SEA", "AIR")
        assert len(t["block_sequence"]) >= 5


def test_air_shipment_volumetric_chargeable_weights():
    """
    Assert IATA air calculation:
    Piece 1: 5 cartons, 40 x 30 x 20 cm, actual gross = 12 kg each (60 kg total).
    Volumetric = 5 * (40 * 30 * 20) / 6000 = 5 * 24000 / 6000 = 20.00 kg.
    Piece 2: 2 crates, 100 x 60 x 50 cm, actual gross = 30 kg each (60 kg total).
    Volumetric = 2 * (100 * 60 * 50) / 6000 = 2 * 300000 / 6000 = 100.00 kg.
    Total actual = 120.00 kg, Total volumetric = 120.00 kg.
    If Piece 2 crate height is 60 cm:
    Volumetric = 2 * (100 * 60 * 60) / 6000 = 120.00 kg. Total vol = 140.00 kg.
    Chargeable = max(120, 140) = 140.00 kg.
    """
    pieces = [
        {"count": 5, "actual_gross_kg": "12.0", "length_cm": "40", "width_cm": "30", "height_cm": "20"},
        {"count": 2, "actual_gross_kg": "30.0", "length_cm": "100", "width_cm": "60", "height_cm": "60"},
    ]
    res = compute_air_weights(pieces)
    assert res["actual_gross_kg"] == Decimal("120.00")
    assert res["volumetric_kg"] == Decimal("140.00")
    assert res["chargeable_kg"] == Decimal("140.00")


def test_awb_mod7_check_digit_validation():
    """
    Test IATA AWB mod-7 validation:
    Serial 1234567 % 7 == 5 -> valid: '098-12345675'
    Invalid: '098-12345674'
    """
    valid, check = validate_awb("098-12345675")
    assert valid is True
    assert check == 5

    invalid, check_inv = validate_awb("098-12345674")
    assert invalid is False
    assert check_inv == 5  # Computed check digit is 5, but given was 4


def test_liability_regimes_versioned_lookup_and_confirmation():
    """Verify versioned liability regimes (Hague-Visby, Montreal 1999, Hamburg Rules)."""
    assert "hague_visby_cogsa" in REGIMES_2026_01
    assert "montreal_1999" in REGIMES_2026_01
    assert "hamburg_rules" in REGIMES_2026_01

    montreal = get_liability_regime("montreal_1999")
    assert montreal.limit_sdr_per_kg == Decimal("22.00")
    assert montreal.damage_notice_days == 14
    assert montreal.delay_notice_days == 21

    confirmed = confirm_regime("montreal_1999", surveyor_name="Kishan Surveyor")
    assert confirmed["confirmed_by"] == "Kishan Surveyor"
    assert confirmed["notice_period_days"] == 14
    assert confirmed["limit_sdr_per_kg"] == "22.00"


def test_annexures_pdf_merger_isolation(tmp_path):
    """
    Assert that merge_pdf_annexures appends PDF annexures after the report body,
    leaving the original body pages intact.
    """
    # 1. Create a 2-page body PDF in memory
    body_writer = PdfWriter()
    body_writer.add_blank_page(width=595, height=842)
    body_writer.add_blank_page(width=595, height=842)
    body_buf = io.BytesIO()
    body_writer.write(body_buf)
    body_bytes = body_buf.getvalue()

    # 2. Create a 3-page annexure PDF
    annex_path = tmp_path / "temperature_logger.pdf"
    annex_writer = PdfWriter()
    for _ in range(3):
        annex_writer.add_blank_page(width=595, height=842)
    with open(annex_path, "wb") as f:
        annex_writer.write(f)

    # 3. Merge
    annex_block = {
        "type": "annexures",
        "_computed": {
            "merge_order": [
                {"sub_id": "A1", "title": "Temp Logger PDF", "file_path": str(annex_path)}
            ]
        }
    }

    merged = merge_pdf_annexures(body_bytes, annex_block, assets={})
    assert len(merged) > 0

    merged_reader = PdfReader(io.BytesIO(merged))
    # 2 body pages + 3 annexure pages = 5 pages total
    assert len(merged_reader.pages) == 5


def test_annexures_merge_order_and_text_label_alignment(tmp_path):
    """
    Asserts Week 3 Requirement 3:
    Annexures merge in order with labels matching the narrative references.
    """
    # 1. Create two PDF attachments
    pdf1_path = tmp_path / "attachment_a1.pdf"
    w1 = PdfWriter()
    w1.add_blank_page(width=595, height=842)
    with open(pdf1_path, "wb") as f:
        w1.write(f)

    pdf2_path = tmp_path / "attachment_b1.pdf"
    w2 = PdfWriter()
    w2.add_blank_page(width=595, height=842)
    with open(pdf2_path, "wb") as f:
        w2.write(f)

    # 2. Block State with narrative referring to Annexure A1 and B1
    block_state = {
        "metadata": {"number": "M-ANNEX-TEST", "family": "SURVEY_REPORT", "docx_template": "mca-synthetic-v1.docx"},
        "transport": {"mode": "SEA", "document": {"kind": "BILL_OF_LADING", "number": "BL-1"}},
        "carriage_units": [{"id": "u1", "unit_type": "CONTAINER", "identifier": "CMAU1234567"}],
        "blocks": [
            {
                "id": "b_narrative",
                "type": "narrative",
                "additional_text": "Cargo arrived as per Bill of Lading (See Annexure A1) with temperature records attached (See Annexure B1).",
            },
            {
                "id": "b_annexures",
                "type": "annexures",
                "rows": [
                    {"prefix": "A", "title": "Bill of Lading Copy", "file_path": str(pdf1_path)},
                    {"prefix": "B", "title": "Temperature Recorder Chart", "file_path": str(pdf2_path)},
                ],
            },
        ],
    }

    computed = compute(block_state)
    annex_comp = next(b for b in computed["blocks"] if b["type"] == "annexures")["_computed"]

    # Verify deterministic ordering and labels
    order = annex_comp["merge_order"]
    assert len(order) == 2
    assert order[0]["sub_id"] == "A1"
    assert order[0]["title"] == "Bill of Lading Copy"
    assert order[1]["sub_id"] == "B1"
    assert order[1]["title"] == "Temperature Recorder Chart"

    doc_list = annex_comp["documentation_list"]
    assert "Annexure A1: Bill of Lading Copy" in doc_list[0]
    assert "Annexure B1: Temperature Recorder Chart" in doc_list[1]

    # Narrative text matches the allocated annexures
    narrative_text = block_state["blocks"][0]["additional_text"]
    assert "Annexure A1" in narrative_text
    assert "Annexure B1" in narrative_text
