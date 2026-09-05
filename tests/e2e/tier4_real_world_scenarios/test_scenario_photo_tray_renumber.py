"""
Tier 4: Real-World Application Scenarios - Scenario 5: Photo Tray Renumbering & Word Plate Generation.
Covers:
Full workflow of photo management and dynamic renumbering:
- Uploading 12 photos and recording bit-exact SHA-256 hashes
- Grouping photos into 3 observation groups
- Deriving photo range references in narrative
- Simulating surveyor deleting photo #3 and moving photo #6
- Automatic dynamic re-derivation without numbering gaps
- 2-column Word photo plate table structure
"""

import hashlib
import pytest
import docx
from tests.e2e.helpers.contract_stubs import reference_photo_ranges
from tests.e2e.helpers.synthetic_data import create_synthetic_image_with_exif


@pytest.mark.tier4
def test_scenario_photo_tray_renumbering_and_word_plate():
    """
    Simulates photo tray manipulation during survey editing and Word plate assembly.
    """
    # 1. Simulate 12 photo uploads with bit-exact SHA-256 hashes
    photos = {}
    for i in range(1, 13):
        asset_id = f"photo_{i:02d}"
        raw = create_synthetic_image_with_exif(1200, 800, camera_model=f"SurveyCam-{i}")
        sha = hashlib.sha256(raw).hexdigest()
        photos[asset_id] = {"bytes": raw, "sha256": sha}

    assert len(photos) == 12

    # 2. Partition into 3 observation groups:
    # Group 1: 4 photos (1..4) -> (Photo Nos. 1 to 4)
    # Group 2: 2 photos (5..6) -> (Photo Nos. 5 & 6)
    # Group 3: 6 photos (7..12) -> (Photo Nos. 7 to 12)
    groups = [
        {"id": "g1_seals", "observation": "Container exterior and seals", "asset_ids": [f"photo_{i:02d}" for i in range(1, 5)]},
        {"id": "g2_loggers", "observation": "Temperature loggers recovered from cargo", "asset_ids": [f"photo_{i:02d}" for i in range(5, 7)]},
        {"id": "g3_cargo", "observation": "Cargo inspected upon destuffing", "asset_ids": [f"photo_{i:02d}" for i in range(7, 13)]}
    ]

    res_initial = reference_photo_ranges(groups)
    assert res_initial["g1_seals"]["label"] == "(Photo Nos. 1 to 4)"
    assert res_initial["g2_loggers"]["label"] == "(Photo Nos. 5 & 6)"
    assert res_initial["g3_cargo"]["label"] == "(Photo Nos. 7 to 12)"

    # 3. Surveyor Edit Action:
    # Delete photo_03 (blurry photo) from Group 1
    # Move photo_06 from Group 2 to Group 1
    groups[0]["asset_ids"].remove("photo_03")  # g1 now has photo_01, photo_02, photo_04 (3 photos)
    groups[1]["asset_ids"].remove("photo_06")  # g2 now has photo_05 (1 photo)
    groups[0]["asset_ids"].append("photo_06")  # g1 now has photo_01, photo_02, photo_04, photo_06 (4 photos)

    # 4. Automatic dynamic re-derivation
    res_updated = reference_photo_ranges(groups)

    # Group 1: 4 photos -> (Photo Nos. 1 to 4)
    assert res_updated["g1_seals"]["label"] == "(Photo Nos. 1 to 4)"
    assert res_updated["g1_seals"]["count"] == 4

    # Group 2: 1 photo -> (Photo No. 5) [singular 'No.']
    assert res_updated["g2_loggers"]["label"] == "(Photo No. 5)"
    assert res_updated["g2_loggers"]["count"] == 1

    # Group 3: 6 photos -> (Photo Nos. 6 to 11) [shifted by 1 because 1 was deleted overall]
    assert res_updated["g3_cargo"]["label"] == "(Photo Nos. 6 to 11)"
    assert res_updated["g3_cargo"]["count"] == 6

    # Invariant: Total count is 4 + 1 + 6 = 11 (was 12, 1 deleted). Exhaustive and contiguous!
    assert res_updated["g3_cargo"]["end"] == 11

    # 5. Word 2-Column Photo Plate Construction
    doc = docx.Document()
    table = doc.add_table(rows=0, cols=2)
    # Configure 2 columns with images and centered captions
    total_rendered_cells = 0
    current_photo_idx = 1
    for g in groups:
        for aid in g["asset_ids"]:
            if total_rendered_cells % 2 == 0:
                row_cells = table.add_row().cells
            col_idx = total_rendered_cells % 2
            cell = row_cells[col_idx]
            cell.paragraphs[0].text = f"Photo No. {current_photo_idx}: {g['observation']}"
            current_photo_idx += 1
            total_rendered_cells += 1

    assert len(table.columns) == 2
    assert total_rendered_cells == 11
    # Check that last cell text matches Photo No. 11
    last_cell_text = table.rows[-1].cells[0].text
    assert "Photo No. 11" in last_cell_text
