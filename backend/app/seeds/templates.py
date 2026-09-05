"""
The Six Canonical Report Templates — Master Spec §8.

Grid of cargo class x transport mode + QC variant:
1. General Cargo – Sea Shipment (Survey, Sea)
2. General Cargo – Air Shipment (Survey, Air)
3. Perishable Cargo – Sea Shipment (Survey, Sea)
4. Perishable Cargo – Air Shipment (Survey, Air)
5. Perishable Cargo QC Report – Sea Shipment (QC, Sea)
6. Perishable Cargo QC Report – Air Shipment (QC, Air)
"""

from typing import Any, Dict, List

SIX_CANONICAL_TEMPLATES: List[Dict[str, Any]] = [
    {
        "id": "general_cargo_sea_survey",
        "name": "General Cargo – Sea Survey Report",
        "family": "SURVEY_REPORT",
        "mode": "SEA",
        "block_sequence": [
            {"id": "b_parties", "type": "parties", "scope": "SHIPMENT"},
            {"id": "b_attendance", "type": "attendance", "scope": "SHIPMENT"},
            {"id": "b_particulars", "type": "particulars", "scope": "SHIPMENT"},
            {"id": "b_timeline", "type": "timeline", "scope": "SHIPMENT"},
            {"id": "b_narrative_circ", "type": "narrative", "section": "CIRCUMSTANCES OF LOSS"},
            {"id": "b_unit_group", "type": "unit_group", "repeat_for": "carriage_units"},
            {"id": "b_inventory", "type": "inventory", "scope": "SHIPMENT"},
            {"id": "b_reconciliation", "type": "reconciliation", "scope": "SHIPMENT", "rolls_up_from": "b_unit_group.reconciliation"},
            {"id": "b_narrative_cause", "type": "narrative", "section": "CAUSE OF LOSS & LIABILITY"},
            {"id": "b_photos", "type": "photo_plate", "series_id": "survey"},
            {"id": "b_annexures", "type": "annexures", "scope": "SHIPMENT"},
            {"id": "b_disclaimer", "type": "fixed_text", "key": "disclaimer@v2"},
        ],
    },
    {
        "id": "general_cargo_air_survey",
        "name": "General Cargo – Air Survey Report",
        "family": "SURVEY_REPORT",
        "mode": "AIR",
        "block_sequence": [
            {"id": "b_parties", "type": "parties", "scope": "SHIPMENT"},
            {"id": "b_attendance", "type": "attendance", "scope": "SHIPMENT"},
            {"id": "b_particulars", "type": "particulars", "scope": "SHIPMENT"},
            {"id": "b_timeline", "type": "timeline", "scope": "SHIPMENT"},
            {"id": "b_unit_group", "type": "unit_group", "repeat_for": "carriage_units"},
            {"id": "b_inventory", "type": "inventory", "scope": "SHIPMENT"},
            {"id": "b_reconciliation", "type": "reconciliation", "scope": "SHIPMENT"},
            {"id": "b_narrative_cause", "type": "narrative", "section": "CAUSE OF LOSS & GROUND HANDLING"},
            {"id": "b_photos", "type": "photo_plate", "series_id": "survey"},
            {"id": "b_annexures", "type": "annexures", "scope": "SHIPMENT"},
            {"id": "b_disclaimer", "type": "fixed_text", "key": "disclaimer@v2"},
        ],
    },
    {
        "id": "perishable_sea_survey",
        "name": "Perishable Cargo – Sea Survey Report",
        "family": "SURVEY_REPORT",
        "mode": "SEA",
        "block_sequence": [
            {"id": "b_parties", "type": "parties", "scope": "SHIPMENT"},
            {"id": "b_attendance", "type": "attendance", "scope": "SHIPMENT"},
            {"id": "b_particulars", "type": "particulars", "scope": "SHIPMENT"},
            {"id": "b_timeline", "type": "timeline", "scope": "SHIPMENT"},
            {"id": "b_unit_group", "type": "unit_group", "repeat_for": "carriage_units"},
            {"id": "b_reconciliation", "type": "reconciliation", "scope": "SHIPMENT", "rolls_up_from": "b_unit_group.reconciliation"},
            {"id": "b_narrative_cause", "type": "narrative", "section": "CAUSE OF LOSS & FINDINGS"},
            {"id": "b_photos", "type": "photo_plate", "series_id": "survey"},
            {"id": "b_annexures", "type": "annexures", "scope": "SHIPMENT"},
            {"id": "b_disclaimer", "type": "fixed_text", "key": "disclaimer@v2"},
        ],
    },
    {
        "id": "perishable_air_survey",
        "name": "Perishable Cargo – Air Survey Report",
        "family": "SURVEY_REPORT",
        "mode": "AIR",
        "block_sequence": [
            {"id": "b_parties", "type": "parties", "scope": "SHIPMENT"},
            {"id": "b_attendance", "type": "attendance", "scope": "SHIPMENT"},
            {"id": "b_particulars", "type": "particulars", "scope": "SHIPMENT"},
            {"id": "b_timeline", "type": "timeline", "scope": "SHIPMENT"},
            {"id": "b_measurements", "type": "measurements"},
            {"id": "b_table", "type": "table"},
            {"id": "b_reconciliation", "type": "reconciliation", "scope": "SHIPMENT"},
            {"id": "b_narrative_cause", "type": "narrative", "section": "CAUSE OF LOSS & COOL CHAIN BREAK"},
            {"id": "b_photos", "type": "photo_plate", "series_id": "survey"},
            {"id": "b_annexures", "type": "annexures", "scope": "SHIPMENT"},
            {"id": "b_disclaimer", "type": "fixed_text", "key": "disclaimer@v2"},
        ],
    },
    {
        "id": "perishable_qc_sea",
        "name": "Perishable Cargo QC Report – Sea Shipment",
        "family": "QC_REPORT",
        "mode": "SEA",
        "block_sequence": [
            {"id": "b1", "type": "particulars"},
            {"id": "b2", "type": "narrative"},
            {"id": "b3", "type": "measurements"},
            {"id": "b4", "type": "table"},
            {"id": "b5", "type": "photo_plate"},
            {"id": "b6", "type": "fixed_text"},
        ],
    },
    {
        "id": "perishable_qc_air",
        "name": "Perishable Cargo QC Report – Air Shipment",
        "family": "QC_REPORT",
        "mode": "AIR",
        "block_sequence": [
            {"id": "b1", "type": "particulars"},
            {"id": "b2", "type": "timeline"},
            {"id": "b3", "type": "narrative"},
            {"id": "b4", "type": "measurements"},
            {"id": "b5", "type": "table"},
            {"id": "b6", "type": "photo_plate"},
            {"id": "b7", "type": "fixed_text"},
        ],
    },
]

# Aliases for UI dropdowns
SIX_CANONICAL_TEMPLATES.extend([
    {
        "id": "perishable-qc-sea",
        "name": "Perishable Cargo QC Report – Sea Shipment",
        "family": "QC_REPORT",
        "mode": "SEA",
        "block_sequence": SIX_CANONICAL_TEMPLATES[4]["block_sequence"],
    },
    {
        "id": "perishable-qc-air",
        "name": "Perishable Cargo QC Report – Air Shipment",
        "family": "QC_REPORT",
        "mode": "AIR",
        "block_sequence": SIX_CANONICAL_TEMPLATES[5]["block_sequence"],
    },
    {
        "id": "general-cargo-sea",
        "name": "General Cargo – Sea Survey Report",
        "family": "SURVEY_REPORT",
        "mode": "SEA",
        "block_sequence": SIX_CANONICAL_TEMPLATES[0]["block_sequence"],
    },
    {
        "id": "general-cargo-air",
        "name": "General Cargo – Air Survey Report",
        "family": "SURVEY_REPORT",
        "mode": "AIR",
        "block_sequence": SIX_CANONICAL_TEMPLATES[1]["block_sequence"],
    },
    {
        "id": "perishable-survey-sea",
        "name": "Perishable Cargo – Sea Survey Report",
        "family": "SURVEY_REPORT",
        "mode": "SEA",
        "block_sequence": SIX_CANONICAL_TEMPLATES[2]["block_sequence"],
    },
    {
        "id": "perishable-survey-air",
        "name": "Perishable Cargo – Air Survey Report",
        "family": "SURVEY_REPORT",
        "mode": "AIR",
        "block_sequence": SIX_CANONICAL_TEMPLATES[3]["block_sequence"],
    },
])
