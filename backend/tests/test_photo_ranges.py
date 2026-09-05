"""
Unit tests for photo_ranges.py — photo number computation and integrity assertions.
Tests CRITICAL-RULES §3:
  - Numbers computed, never stored
  - Contiguous, no gaps, every photo in exactly one group
  - Correct range label format
"""

import pytest
from app.compute.photo_ranges import compute_photo_ranges, assert_series_integrity


class TestPhotoRangeLabels:
    def test_single_photo(self):
        groups = [{"id": "g1", "observation": "Door", "asset_ids": ["a1"]}]
        result = compute_photo_ranges(groups)
        assert result["groups"]["g1"]["label"] == "(Photo No. 1)"

    def test_pair_photos(self):
        groups = [{"id": "g1", "observation": "Door", "asset_ids": ["a1", "a2"]}]
        result = compute_photo_ranges(groups)
        assert result["groups"]["g1"]["label"] == "(Photo Nos. 1 & 2)"

    def test_range_photos(self):
        groups = [{"id": "g1", "observation": "Cargo", "asset_ids": ["a1", "a2", "a3", "a4", "a5"]}]
        result = compute_photo_ranges(groups)
        assert result["groups"]["g1"]["label"] == "(Photo Nos. 1 to 5)"

    def test_mandarin_scenario(self):
        """From the mandarin test case: pg1=1&2, pg2=3, pg3=4to6."""
        groups = [
            {"id": "pg1", "observation": "Container doors", "asset_ids": ["img1", "img2"]},
            {"id": "pg2", "observation": "Pulp temperature", "asset_ids": ["img3"]},
            {"id": "pg3", "observation": "Decay damage", "asset_ids": ["img4", "img5", "img6"]},
        ]
        result = compute_photo_ranges(groups)
        assert result["groups"]["pg1"]["label"] == "(Photo Nos. 1 & 2)"
        assert result["groups"]["pg2"]["label"] == "(Photo No. 3)"
        assert result["groups"]["pg3"]["label"] == "(Photo Nos. 4 to 6)"

    def test_start_number_offset(self):
        """Shared-series: start from photo 41."""
        groups = [{"id": "g1", "observation": "X", "asset_ids": ["a1", "a2", "a3", "a4"]}]
        result = compute_photo_ranges(groups, start_number=41)
        assert result["groups"]["g1"]["label"] == "(Photo Nos. 41 to 44)"
        assert result["groups"]["g1"]["start"] == 41
        assert result["groups"]["g1"]["end"] == 44

    def test_next_number_advances_correctly(self):
        groups = [
            {"id": "g1", "observation": "A", "asset_ids": ["a1", "a2"]},
            {"id": "g2", "observation": "B", "asset_ids": ["a3"]},
        ]
        result = compute_photo_ranges(groups, start_number=10)
        assert result["next_number"] == 13
        assert result["total_photos"] == 3

    def test_total_photos_count(self):
        groups = [
            {"id": "g1", "asset_ids": ["a1", "a2", "a3"]},
            {"id": "g2", "asset_ids": ["a4", "a5"]},
        ]
        result = compute_photo_ranges(groups)
        assert result["total_photos"] == 5


class TestPhotoRangeIntegrityAssertions:
    def test_empty_group_raises(self):
        groups = [{"id": "g1", "observation": "X", "asset_ids": []}]
        with pytest.raises(AssertionError, match="empty"):
            compute_photo_ranges(groups)

    def test_duplicate_photo_across_groups_raises(self):
        groups = [
            {"id": "g1", "observation": "A", "asset_ids": ["a1", "a2"]},
            {"id": "g2", "observation": "B", "asset_ids": ["a2", "a3"]},  # a2 duplicate
        ]
        with pytest.raises(AssertionError, match="multiple"):
            compute_photo_ranges(groups)

    def test_assert_series_integrity_valid(self):
        groups = [
            {"id": "g1", "asset_ids": ["a1", "a2"]},
            {"id": "g2", "asset_ids": ["a3", "a4", "a5"]},
        ]
        # Should not raise
        assert_series_integrity(groups, start_number=1)

    def test_renumber_after_delete(self):
        """
        CRITICAL RULE: Deleting a photo must renumber all subsequent photos.
        Simulate by recomputing with one asset removed.
        """
        original = [
            {"id": "g1", "asset_ids": ["a1", "a2", "a3"]},
            {"id": "g2", "asset_ids": ["a4", "a5"]},
        ]
        result_before = compute_photo_ranges(original)
        assert result_before["groups"]["g2"]["start"] == 4

        # Delete a3 from g1
        modified = [
            {"id": "g1", "asset_ids": ["a1", "a2"]},       # a3 deleted
            {"id": "g2", "asset_ids": ["a4", "a5"]},
        ]
        result_after = compute_photo_ranges(modified)
        # g2 should now start at 3, not 4
        assert result_after["groups"]["g2"]["start"] == 3
        assert result_after["groups"]["g2"]["label"] == "(Photo Nos. 3 & 4)"

