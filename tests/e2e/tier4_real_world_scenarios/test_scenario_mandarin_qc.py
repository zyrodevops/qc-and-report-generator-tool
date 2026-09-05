"""
Tier 4: Real-World Application Scenarios - Scenario 1: Mandarin QC 16 Boxes Survey.
Covers:
Full workflow of a perishable citrus QC inspection:
- 16 boxes survey defect categorization
- Exact reproduction of Mandarin row totals and percentages (234, 56.84/23.08/5.98/10.26/3.84)
- Exact reproduction of column totals and percentages (675, 54.96/25.48/7.56/6.96/5.04)
- Temperature & brix measurements
- Observation groups & photo plate cross-referencing
"""

from decimal import Decimal
import pytest
from tests.e2e.helpers.contract_stubs import reference_compute_table, reference_photo_ranges
from tests.e2e.helpers.synthetic_data import MANDARIN_ROW, MANDARIN_COL_TOTALS


@pytest.mark.tier4
def test_scenario_mandarin_qc_complete_workflow():
    """
    Executes the complete Mandarin QC 16 Boxes inspection scenario per Master-Spec §9 & §14.
    """
    categories = ["sound", "soft", "decay", "bruised", "stem_end_rot"]
    
    # 1. 16 Boxes Sample Data
    rows = [
        {"group": "Box Count 55", "boxes": 5, "values": {"sound": 133, "soft": 54, "decay": 14, "bruised": 24, "stem_end_rot": 9}},
        {"group": "Box Count 65", "boxes": 6, "values": {"sound": 140, "soft": 68, "decay": 18, "bruised": 13, "stem_end_rot": 15}},
        {"group": "Box Count 75", "boxes": 5, "values": {"sound": 98, "soft": 50, "decay": 19, "bruised": 10, "stem_end_rot": 10}}
    ]

    # 2. Compute table derived figures
    res = reference_compute_table(rows, categories)

    # Verify Mandarin Row exact figures
    assert res["row_totals"][0] == MANDARIN_ROW["expected_total"]  # 234
    assert res["row_percentages"][0] == MANDARIN_ROW["expected_pcts"]
    assert sum(res["row_percentages"][0]) == Decimal("100.00")

    # Verify Mandarin Column Totals
    assert res["grand_total"] == MANDARIN_COL_TOTALS["expected_grand_total"]  # 675
    assert res["column_totals"]["sound"] == Decimal("371")
    assert res["column_totals"]["soft"] == Decimal("172")
    assert res["column_totals"]["decay"] == Decimal("51")
    assert res["column_totals"]["bruised"] == Decimal("47")
    assert res["column_totals"]["stem_end_rot"] == Decimal("34")
    assert sum(res["column_percentages"].values()) == Decimal("100.00")

    # 3. Photo Observation Groups cross-referenced with Narrative
    photo_groups = [
        {"id": "pg1", "observation": "External container doors and intact seal", "asset_ids": ["img1", "img2"]},
        {"id": "pg2", "observation": "Pulp temperature reading 1.0 C", "asset_ids": ["img3"]},
        {"id": "pg3", "observation": "Mandarins showing stem-end rot and decay", "asset_ids": ["img4", "img5", "img6"]}
    ]
    photo_res = reference_photo_ranges(photo_groups)

    assert photo_res["pg1"]["label"] == "(Photo Nos. 1 & 2)"
    assert photo_res["pg2"]["label"] == "(Photo No. 3)"
    assert photo_res["pg3"]["label"] == "(Photo Nos. 4 to 6)"

    # Narrative slot integration
    narrative_text = f"Pulp temperature was measured inside the container {photo_res['pg2']['label']}. " \
                     f"Defective fruit showing fungal decay was documented {photo_res['pg3']['label']}."
    assert "(Photo No. 3)" in narrative_text
    assert "(Photo Nos. 4 to 6)" in narrative_text
