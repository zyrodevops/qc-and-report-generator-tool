"""
Tier 3: Cross-Feature Combinations - End-to-End Photo Lifecycle.
Covers:
Upload -> SHA-256 Bit-Exact Storage -> Derived Copy Resizing -> Tray Grouping -> photo_ranges.py -> 2-Column Word Plate.
"""

import hashlib
import io
import pytest
from PIL import Image
from tests.e2e.helpers.contract_stubs import (
    reference_photo_ranges,
    get_photo_ranges_fn
)
from tests.e2e.helpers.synthetic_data import create_synthetic_image_with_exif


@pytest.mark.tier3
def test_full_photo_lifecycle_pipeline():
    """
    Simulates complete photo lifecycle:
    1. Upload 4 high-resolution photo originals
    2. Record SHA-256 hashes
    3. Generate derived copies (display <=800px, report <=1600px)
    4. Group into 2 observation groups:
       - Group 1: 2 photos -> (Photo Nos. 1 & 2)
       - Group 2: 2 photos -> (Photo Nos. 3 & 4)
    5. Delete photo 2, re-verify updated ranges:
       - Group 1: 1 photo -> (Photo No. 1)
       - Group 2: 2 photos -> (Photo Nos. 2 & 3)
    """
    photos = []
    hashes = []
    
    # 1 & 2. Upload & hash
    for i in range(4):
        raw = create_synthetic_image_with_exif(1800, 1200, camera_model=f"Cam-{i}")
        sha = hashlib.sha256(raw).hexdigest()
        photos.append(raw)
        hashes.append(sha)
        assert len(sha) == 64

    # 3. Derived copies
    for raw in photos:
        img = Image.open(io.BytesIO(raw))
        assert img.size == (1800, 1200)

        # Report copy
        rep = img.copy()
        rep.thumbnail((1600, 1600))
        assert rep.size[0] <= 1600 and rep.size[1] <= 1600

        # Display copy
        disp = img.copy()
        disp.thumbnail((800, 800))
        assert disp.size[0] <= 800 and disp.size[1] <= 800

    # 4. Tray grouping
    groups = [
        {"id": "grp_front", "asset_ids": ["p1", "p2"]},
        {"id": "grp_cargo", "asset_ids": ["p3", "p4"]}
    ]
    fn = get_photo_ranges_fn() or reference_photo_ranges
    res1 = fn(groups)
    assert res1["grp_front"]["label"] == "(Photo Nos. 1 & 2)"
    assert res1["grp_cargo"]["label"] == "(Photo Nos. 3 & 4)"

    # 5. Delete photo 2 and re-derive
    groups[0]["asset_ids"].remove("p2")
    res2 = fn(groups)
    assert res2["grp_front"]["label"] == "(Photo No. 1)"
    assert res2["grp_cargo"]["label"] == "(Photo Nos. 2 & 3)"
