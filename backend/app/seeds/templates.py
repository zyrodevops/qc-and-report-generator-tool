"""
Canonical report templates.

Block sequences are derived from the corpus analysis of 451 of the client's own reports.
See IMPLEMENTATION-SPEC-perishable-fruits.md sections 1.1 and 1.2.

Two corrections from the original version of this file:

1. The alias block at the end (hyphenated duplicate ids) has been removed. It seeded the
   templates table twice, giving 12 rows for 6 real report types, which is why the report
   type dropdown looked wrong.

2. The perishable survey template had ONE narrative block labelled
   "CAUSE OF LOSS & FINDINGS". The corpus has SEVEN distinct text sections, with these
   coverage rates across 439 fruit reports:

       APPLICATION            99%
       CIRCUMSTANCES_OF_LOSS  97%
       OUR_SURVEY             98%
       CONDITION_FOUND        46%   (fruit-gated: 100% Blueberry, 0% Grapes/Plum/Mandarins/Avocado)
       CAUSE_OF_LOSS          90%
       NEXT_STEP              96%
       DOCUMENTATION          98%

   Photos sit AFTER Documentation as one contiguous block, matching M-159-2026 and the
   client's request that all text stay together and all photos stay together.

Section keys are names, never paragraph numbers: Cause of Loss is "PARAGRAPH 3" in 332
reports and "PARAGRAPH 4" in 57.
"""

from typing import Any, Dict, List

# Section identifiers used by the clause library. Keep in sync with the
# `section` column of D:/marine-corpus/analysis/clause_library.csv.
SECTION_APPLICATION = "APPLICATION"
SECTION_CIRCUMSTANCES = "CIRCUMSTANCES_OF_LOSS"
SECTION_OUR_SURVEY = "OUR_SURVEY"
SECTION_CONDITION_FOUND = "CONDITION_FOUND"
SECTION_CAUSE_OF_LOSS = "CAUSE_OF_LOSS"
SECTION_NEXT_STEP = "NEXT_STEP"
SECTION_DOCUMENTATION = "DOCUMENTATION"
SECTION_SUMMARY = "SUMMARY"


def _perishable_survey_blocks(mode: str) -> List[Dict[str, Any]]:
    """Final Survey Report for perishable cargo. Spec section 1.1."""
    return [
        {"id": "b_particulars", "type": "particulars", "scope": "SHIPMENT"},
        {"id": "b_parties", "type": "parties", "scope": "SHIPMENT"},
        {"id": "b_attendance", "type": "attendance", "scope": "SHIPMENT"},
        {"id": "b_timeline", "type": "timeline", "scope": "SHIPMENT", "mode": mode},

        {"id": "b_application", "type": "narrative",
         "section": SECTION_APPLICATION, "coverage": 99, "removable": True},
        {"id": "b_circumstances", "type": "narrative",
         "section": SECTION_CIRCUMSTANCES, "coverage": 97, "removable": True},

        # Repeats per survey visit, not per container. M-159-2026 has OUR SURVEY 2.1
        # (11 Sept) and 2.2 (12 Sept), each with its own CONDITION FOUND.
        {"id": "b_survey_visit", "type": "unit_group", "repeat_for": "survey_visits",
         "heading_template": "PARAGRAPH 2.{index}: OUR SURVEY ON {date}",
         "blocks": [
             {"id": "b_our_survey", "type": "narrative",
              "section": SECTION_OUR_SURVEY, "scope": "UNIT", "coverage": 98},
             {"id": "b_condition_found", "type": "narrative",
              "section": SECTION_CONDITION_FOUND, "scope": "UNIT",
              "coverage": 46, "fruit_gated": "show_condition_found"},
             {"id": "b_defect_table", "type": "table", "scope": "UNIT"},
             {"id": "b_chart", "type": "chart", "scope": "UNIT",
              "source_block": "b_defect_table", "fruit_gated": "show_chart"},
             {"id": "b_measurements", "type": "measurements", "scope": "UNIT"},
         ]},

        {"id": "b_instrument", "type": "instrument", "scope": "SHIPMENT",
         "optional": True},

        {"id": "b_cause_of_loss", "type": "narrative",
         "section": SECTION_CAUSE_OF_LOSS, "coverage": 90, "removable": True},
        {"id": "b_next_step", "type": "narrative",
         "section": SECTION_NEXT_STEP, "coverage": 96, "removable": True},
        {"id": "b_documentation", "type": "narrative",
         "section": SECTION_DOCUMENTATION, "coverage": 98, "removable": True},

        # All photos together, after all text. Client request, matches M-159-2026.
        {"id": "b_photos", "type": "photo_plate", "series_id": "survey",
         "caption_prefix": "Survey Photo No."},
        {"id": "b_annexures", "type": "annexures", "scope": "SHIPMENT"},
        {"id": "b_closing", "type": "fixed_text", "key": "closing@v3",
         "signatures": 2},
    ]


def _perishable_qc_blocks(_mode: str) -> List[Dict[str, Any]]:
    """In-House QC Report. Spec section 1.2. Identical for sea and air.

    Verified against all 3 QC samples. Absent from all three: Application,
    Circumstances, Cause of Loss, Next Step, Documentation, attendance register,
    temperature recorder. QC needs no B/L, no invoice and no logger.
    """
    return [
        {"id": "b_particulars", "type": "particulars", "scope": "SHIPMENT",
         "title": "Cargo Particular"},
        {"id": "b_summary", "type": "narrative", "section": SECTION_SUMMARY},
        {"id": "b_defect_table", "type": "table", "scope": "SHIPMENT"},
        {"id": "b_chart", "type": "chart", "scope": "SHIPMENT",
         "source_block": "b_defect_table", "fruit_gated": "show_chart"},
        {"id": "b_photos", "type": "photo_plate", "series_id": "qc",
         "caption_prefix": "QC Inspection Photo No."},
        {"id": "b_closing", "type": "fixed_text", "key": "closing_qc@v1",
         "signatures": 1},
    ]


def _general_cargo_blocks(mode: str) -> List[Dict[str, Any]]:
    """General cargo survey.

    PROVISIONAL. The only general cargo archive we have is Gladstone Agencies' work,
    not the client's, so no clause library has been derived for it. Structure below is
    carried over from the previous version and must be revisited once the client
    supplies his own general cargo reports.
    """
    return [
        {"id": "b_particulars", "type": "particulars", "scope": "SHIPMENT"},
        {"id": "b_parties", "type": "parties", "scope": "SHIPMENT"},
        {"id": "b_attendance", "type": "attendance", "scope": "SHIPMENT"},
        {"id": "b_timeline", "type": "timeline", "scope": "SHIPMENT", "mode": mode},
        {"id": "b_circumstances", "type": "narrative",
         "section": SECTION_CIRCUMSTANCES, "removable": True},
        {"id": "b_unit_group", "type": "unit_group", "repeat_for": "carriage_units",
         "blocks": [
             {"id": "b_unit_particulars", "type": "particulars", "scope": "UNIT"},
             {"id": "b_unit_observations", "type": "observations", "scope": "UNIT"},
             {"id": "b_unit_reconciliation", "type": "reconciliation", "scope": "UNIT"},
         ]},
        {"id": "b_inventory", "type": "inventory", "scope": "SHIPMENT"},
        {"id": "b_reconciliation", "type": "reconciliation", "scope": "SHIPMENT",
         "rolls_up_from": "b_unit_group.b_unit_reconciliation"},
        {"id": "b_cause_of_loss", "type": "narrative",
         "section": SECTION_CAUSE_OF_LOSS, "removable": True},
        {"id": "b_next_step", "type": "narrative",
         "section": SECTION_NEXT_STEP, "removable": True},
        {"id": "b_documentation", "type": "narrative",
         "section": SECTION_DOCUMENTATION, "removable": True},
        {"id": "b_photos", "type": "photo_plate", "series_id": "survey",
         "caption_prefix": "Survey Photo No."},
        {"id": "b_annexures", "type": "annexures", "scope": "SHIPMENT"},
        {"id": "b_closing", "type": "fixed_text", "key": "closing@v3",
         "signatures": 2},
    ]


SIX_CANONICAL_TEMPLATES: List[Dict[str, Any]] = [
    {
        "id": "perishable_sea_survey",
        "name": "Perishable Cargo – Final Survey Report (Sea)",
        "family": "SURVEY_REPORT",
        "mode": "SEA",
        "cargo_class": "PERISHABLE",
        "block_sequence": _perishable_survey_blocks("SEA"),
    },
    {
        "id": "perishable_air_survey",
        "name": "Perishable Cargo – Final Survey Report (Air)",
        "family": "SURVEY_REPORT",
        "mode": "AIR",
        "cargo_class": "PERISHABLE",
        "block_sequence": _perishable_survey_blocks("AIR"),
    },
    {
        "id": "perishable_qc_sea",
        "name": "Perishable Cargo – In-House QC Report (Sea)",
        "family": "QC_REPORT",
        "mode": "SEA",
        "cargo_class": "PERISHABLE",
        "block_sequence": _perishable_qc_blocks("SEA"),
    },
    {
        "id": "perishable_qc_air",
        "name": "Perishable Cargo – In-House QC Report (Air)",
        "family": "QC_REPORT",
        "mode": "AIR",
        "cargo_class": "PERISHABLE",
        "block_sequence": _perishable_qc_blocks("AIR"),
    },
    {
        "id": "general_cargo_sea_survey",
        "name": "General Cargo – Survey Report (Sea)",
        "family": "SURVEY_REPORT",
        "mode": "SEA",
        "cargo_class": "GENERAL_CARGO",
        "block_sequence": _general_cargo_blocks("SEA"),
    },
    {
        "id": "general_cargo_air_survey",
        "name": "General Cargo – Survey Report (Air)",
        "family": "SURVEY_REPORT",
        "mode": "AIR",
        "cargo_class": "GENERAL_CARGO",
        "block_sequence": _general_cargo_blocks("AIR"),
    },
]

# Ids that older builds seeded as hyphenated duplicates of the six above.
# Reports may already point at them, so startup repoints those reports onto the
# canonical id BEFORE deleting the duplicate row (there is an FK from reports).
LEGACY_TEMPLATE_ID_MAP: Dict[str, str] = {
    "perishable-qc-sea": "perishable_qc_sea",
    "perishable-qc-air": "perishable_qc_air",
    "perishable-survey-sea": "perishable_sea_survey",
    "perishable-survey-air": "perishable_air_survey",
    "general-cargo-sea": "general_cargo_sea_survey",
    "general-cargo-air": "general_cargo_air_survey",
}

LEGACY_DUPLICATE_TEMPLATE_IDS: List[str] = list(LEGACY_TEMPLATE_ID_MAP)
