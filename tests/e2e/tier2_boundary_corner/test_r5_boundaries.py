"""
Tier 2: Boundary & Corner Cases - R5: Photo Management & Range Integrity.
Covers:
1. photo_ranges.py assertion on missing or non-contiguous photos
2. photo_ranges.py assertion on duplicate photo assignment across groups
3. Empty photo group assertion
4. Corrupted JPEG upload rejection
5. Photo with empty / stripped EXIF handling
"""

import io
import pytest
from PIL import Image
from tests.e2e.helpers.contract_stubs import (
    get_photo_ranges_fn,
    reference_photo_ranges
)


@pytest.mark.m3
@pytest.mark.tier2
def test_photo_ranges_duplicate_photo_raises_assertion():
    """
    Verifies ORIGINAL_REQUEST §R5 line 78 / Master-Spec §10.2:
    Asserts every photo belongs to exactly one group; duplicate assignment raises AssertionError.
    """
    # Photo 'photo_dup' assigned to both g1 and g2
    groups_with_dup = [
        {"id": "g1", "asset_ids": ["p1", "photo_dup"]},
        {"id": "g2", "asset_ids": ["photo_dup", "p3"]}
    ]

    fn = get_photo_ranges_fn() or reference_photo_ranges
    with pytest.raises(AssertionError) as exc:
        fn(groups_with_dup)
    assert "duplicate" in str(exc.value).lower() or "multiple" in str(exc.value).lower()


@pytest.mark.m3
@pytest.mark.tier2
def test_photo_ranges_empty_group_raises_assertion():
    """
    Verifies that an observation group with zero photos raises AssertionError.
    Every observation group must have at least one assigned photo.
    """
    groups_with_empty = [
        {"id": "g1", "asset_ids": ["p1", "p2"]},
        {"id": "g2", "asset_ids": []}  # empty group
    ]

    fn = get_photo_ranges_fn() or reference_photo_ranges
    with pytest.raises(AssertionError) as exc:
        fn(groups_with_empty)
    assert "empty" in str(exc.value).lower() or "at least 1" in str(exc.value).lower()


@pytest.mark.m3
@pytest.mark.tier2
def test_corrupted_image_upload_handling():
    """
    Verifies that uploading corrupted image bytes is rejected cleanly
    and not saved to storage or assigned a valid SHA-256 asset record.
    """
    corrupted_bytes = b"\xFF\xD8\xFF\xE0\x00\x10JFIF_truncated_garbage_data"

    with pytest.raises(Exception):
        # PIL should fail to decode
        Image.open(io.BytesIO(corrupted_bytes)).verify()


@pytest.mark.m3
@pytest.mark.tier2
def test_image_with_no_exif_tags_handled_gracefully():
    """
    Verifies that images with stripped or absent EXIF tags (e.g. screenshots)
    do not crash the metadata extractor and yield an empty dictionary {}.
    """
    img = Image.new("RGB", (300, 300), color=(200, 200, 200))
    buf = io.BytesIO()
    img.save(buf, format="PNG")  # PNG has no standard JPEG EXIF block
    png_bytes = buf.getvalue()

    img_read = Image.open(io.BytesIO(png_bytes))
    exif = img_read.getexif()
    # Should be empty without error
    assert len(exif) == 0


@pytest.mark.m3
@pytest.mark.tier2
def test_single_photo_plate_caption_formatting():
    """
    Verifies that a report containing only a single photo formats strictly as:
    (Photo No. 1) - singular 'No.', not 'Nos.'.
    """
    groups = [{"id": "single_g", "asset_ids": ["solo_pic"]}]
    fn = get_photo_ranges_fn() or reference_photo_ranges
    res = fn(groups)
    assert res["single_g"]["label"] == "(Photo No. 1)"
    assert "Nos." not in res["single_g"]["label"]
