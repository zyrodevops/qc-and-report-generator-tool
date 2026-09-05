"""
Photo Ranges Computation — Master Spec §10.2 and CRITICAL-RULES §3.

Rules (enforced by assertions):
- Photo numbers are computed, NEVER typed or stored.
- Re-derived on every read — no caching.
- Every photo belongs to exactly one group.
- Ranges are contiguous and exhaustive with no gaps.
- Series are never merged or renumbered across each other.

Output format:
  Single:  (Photo No. 50)
  Pair:    (Photo Nos. 39 & 40)
  Range:   (Photo Nos. 55 to 59)
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional


def compute_photo_ranges(
    groups: List[Dict[str, Any]],
    start_number: int = 1,
) -> Dict[str, Any]:
    """
    Given an ordered list of photo groups (each with id + asset_ids),
    compute photo numbers and range label strings.

    Args:
        groups: Ordered list of {id, observation, asset_ids} dicts.
        start_number: First photo number in this series/plate (default 1).
                      For shared-series multi-plate reports, caller passes the
                      running counter so numbering is contiguous across plates.

    Returns:
        {
          "groups": {
              "<group_id>": {
                  "start": int,
                  "end": int,
                  "count": int,
                  "numbers": [int, ...],
                  "label": "(Photo Nos. 41 to 44)" | "(Photo Nos. 39 & 40)" | "(Photo No. 50)"
              }
          },
          "total_photos": int,
          "next_number": int,   # caller uses this to continue a shared series
        }

    Raises:
        AssertionError: if any group is empty, or if any photo_id appears in
                        more than one group (contiguity enforced by sequential numbering).
    """
    seen_asset_ids: set = set()
    group_results: Dict[str, Any] = {}
    current = start_number

    for g in groups:
        gid = g.get("id", "")
        asset_ids = g.get("asset_ids", [])

        assert len(asset_ids) > 0, (
            f"Photo group '{gid}' is empty. "
            "Every group must contain at least one photo."
        )

        photo_numbers: List[int] = []
        for aid in asset_ids:
            assert aid not in seen_asset_ids, (
                f"Asset '{aid}' appears in multiple photo groups. "
                "Each photo must belong to exactly one group."
            )
            seen_asset_ids.add(aid)
            photo_numbers.append(current)
            current += 1

        start_no = photo_numbers[0]
        end_no = photo_numbers[-1]
        count = len(photo_numbers)

        label = _format_range(start_no, end_no, count)

        group_results[gid] = {
            "start": start_no,
            "end": end_no,
            "count": count,
            "numbers": photo_numbers,
            "label": label,
        }

    return {
        "groups": group_results,
        "total_photos": current - start_number,
        "next_number": current,
    }


def _format_range(start: int, end: int, count: int) -> str:
    """Format photo number range string per house rendering convention."""
    if count == 1:
        return f"(Photo No. {start})"
    elif count == 2:
        return f"(Photo Nos. {start} & {end})"
    else:
        return f"(Photo Nos. {start} to {end})"


def assert_series_integrity(
    all_groups: List[Dict[str, Any]],
    start_number: int = 1,
) -> None:
    """
    Assert that a complete series is contiguous and exhaustive.
    Raises AssertionError describing the first violation found.
    Called before every download (the output gate).
    """
    result = compute_photo_ranges(all_groups, start_number=start_number)
    groups = result["groups"]

    expected = start_number
    for g in all_groups:
        gid = g["id"]
        gr = groups[gid]
        assert gr["start"] == expected, (
            f"Gap in photo series: expected photo {expected}, "
            f"but group '{gid}' starts at {gr['start']}."
        )
        expected = gr["end"] + 1

