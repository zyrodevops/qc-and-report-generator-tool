"""
Tier 4: Real-World Application Scenarios - Scenario 6: Orange QC 8 Boxes Survey (MMAU1200498).
Covers:
Full workflow of citrus orange QC inspection based on benchmark RGS Exim Pro:
- 8 boxes survey defect categorization across 5 categories (Sound, Russet, Green patch, Mechanical Injury, Rotten)
- Exact reproduction of Orange row totals (144, 160, 176, 200) and balanced percentages
  (Row 1: 61.11%, 11.11%, 20.83%, 6.25%, 0.70% -> exactly 100.00%)
- Exact reproduction of column totals (378, 76, 190, 32, 4) and grand total 680 pcs
- Column percentages: 55.59%, 11.18%, 27.94%, 4.70%, 0.59% (sum = 100.00%)
- Photo plate series: 106 photos, 53 plates with contiguous labels (Photo Nos. 1 & 2) to (Photo Nos. 105 & 106)
"""

from decimal import Decimal
import pytest
from tests.e2e.helpers.contract_stubs import reference_compute_table, reference_photo_ranges, get_backend_compute
from tests.e2e.helpers.synthetic_data import ORANGE_ROW_72, ORANGE_COL_TOTALS


@pytest.mark.tier4
@pytest.mark.m5
def test_scenario_orange_qc_complete_workflow():
    """
    Executes the complete Orange QC 8 Boxes inspection scenario (Container MMAU1200498).
    Derives expected figures directly from the benchmark report:
    sample-data/tally_sheets/Marine cargo/More reports and csv/RGS Exim Pro - In-House QC Report # Orange Container No. MMAU1200498.docx
    """
    categories = ["sound", "russet", "green_patch", "mechanical_injury", "rotten"]

    # 1. 8 Boxes Sample Data across 4 size counts
    rows = [
        {"group": "Count 72 (2 boxes)", "boxes": 2, "values": {"sound": 88, "russet": 16, "green_patch": 30, "mechanical_injury": 9, "rotten": 1}},
        {"group": "Count 80 (2 boxes)", "boxes": 2, "values": {"sound": 91, "russet": 19, "green_patch": 40, "mechanical_injury": 8, "rotten": 2}},
        {"group": "Count 88 (2 boxes)", "boxes": 2, "values": {"sound": 92, "russet": 23, "green_patch": 56, "mechanical_injury": 5, "rotten": 0}},
        {"group": "Count 100 (2 boxes)", "boxes": 2, "values": {"sound": 107, "russet": 18, "green_patch": 64, "mechanical_injury": 10, "rotten": 1}},
    ]

    # 2. Compute table derived figures via reference oracle
    res = reference_compute_table(rows, categories)

    # Verify Row 1 exact figures (Count 72)
    assert res["row_totals"][0] == ORANGE_ROW_72["expected_total"]  # 144
    assert res["row_percentages"][0] == ORANGE_ROW_72["expected_pcts"]
    assert sum(res["row_percentages"][0]) == Decimal("100.00")

    # Verify Column Totals & Grand Total
    assert res["grand_total"] == ORANGE_COL_TOTALS["expected_grand_total"]  # 680
    assert res["column_totals"]["sound"] == Decimal("378")
    assert res["column_totals"]["russet"] == Decimal("76")
    assert res["column_totals"]["green_patch"] == Decimal("190")
    assert res["column_totals"]["mechanical_injury"] == Decimal("32")
    assert res["column_totals"]["rotten"] == Decimal("4")

    # Verify Hare-Niemeyer Balanced Column Percentages
    assert res["column_percentages"]["sound"] == Decimal("55.59")
    assert res["column_percentages"]["russet"] == Decimal("11.18")
    assert res["column_percentages"]["green_patch"] == Decimal("27.94")
    assert res["column_percentages"]["mechanical_injury"] == Decimal("4.70")
    assert res["column_percentages"]["rotten"] == Decimal("0.59")
    assert sum(res["column_percentages"].values()) == Decimal("100.00")

    # 3. Direct backend compute engine validation
    backend_compute = get_backend_compute()
    if backend_compute:
        block_state = {
            "blocks": [
                {
                    "id": "b_orange_table",
                    "type": "table",
                    "unit": "pcs",
                    "categories": [
                        {"key": "sound", "label": "Sound (Pcs)"},
                        {"key": "russet", "label": "Russet (Pcs)"},
                        {"key": "green_patch", "label": "Green patch (Pcs)"},
                        {"key": "mechanical_injury", "label": "Mechanical Injury (Pcs)"},
                        {"key": "rotten", "label": "Rotten (Pcs)"},
                    ],
                    "rows": [
                        {"label": r["group"], "values": r["values"]}
                        for r in rows
                    ]
                }
            ]
        }
        computed_state = backend_compute(block_state)
        comp = computed_state["blocks"][0]["_computed"]
        assert comp["grand_total"] == Decimal("680.00")
        assert comp["column_percentages"]["sound"] == Decimal("55.59")
        assert comp["column_percentages"]["russet"] == Decimal("11.18")
        assert comp["column_percentages"]["green_patch"] == Decimal("27.94")
        assert comp["column_percentages"]["mechanical_injury"] == Decimal("4.70")
        assert comp["column_percentages"]["rotten"] == Decimal("0.59")
        assert sum(comp["column_percentages"].values()) == Decimal("100.00")

    # 4. Photo Plate Series Validation (106 photos -> 53 pairs)
    photo_groups = [
        {
            "id": f"plate_{p}",
            "observation": f"QC inspection sample {p}",
            "asset_ids": [f"orange_img_{2*p-1}", f"orange_img_{2*p}"]
        }
        for p in range(1, 54)  # 53 plates = 106 photos
    ]
    photo_res = reference_photo_ranges(photo_groups)
    assert len(photo_res) == 53
    assert photo_res["plate_1"]["label"] == "(Photo Nos. 1 & 2)"
    assert photo_res["plate_53"]["label"] == "(Photo Nos. 105 & 106)"
    assert photo_res["plate_53"]["end"] == 106
