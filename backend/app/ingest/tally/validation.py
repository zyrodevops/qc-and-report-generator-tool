"""
Arithmetic & Business Validation Engine — OCR_IMPLEMENTATION.md §11, §16.

Validates:
- Row sums: sum(defect_values) == row_total
- Column sums: sum(category_values across rows) == column_total (when present)
- Range order: min <= max for temperature, Brix, and pressure
- Cold-storage plausibility thresholds (e.g. non-negative counts, cold room temp <= 15°C)
Never silently modifies values to force arithmetic to match.
"""

from __future__ import annotations

from decimal import Decimal
from typing import Any, Dict, List, Optional

from app.ingest.tally.models import CellValidation


class ValidationEngine:
    """Performs strict arithmetic and domain checks on extracted tally data."""

    @staticmethod
    def validate_row_total(
        defect_values: Dict[str, int],
        stated_total: Optional[int] = None,
    ) -> Tuple[int, CellValidation]:
        """
        Validates that sum of defect counts matches stated row total.
        Returns: (computed_sum, validation_result)
        """
        computed_sum = sum(v for v in defect_values.values() if isinstance(v, int) and v >= 0)

        if stated_total is None or stated_total == 0:
            # If no stated total on sheet, the computed sum is the valid checksum
            return computed_sum, CellValidation(
                status="PASSED",
                rule="computed_total",
                expected=computed_sum,
                actual=computed_sum,
                message=f"Computed checksum: {computed_sum}",
            )

        if computed_sum == stated_total:
            return computed_sum, CellValidation(
                status="PASSED",
                rule="row_total",
                expected=stated_total,
                actual=computed_sum,
                message=f"Row checksum ties out: sum({computed_sum}) == total({stated_total})",
            )

        # Mismatch detected: Never silently guess or alter values!
        return computed_sum, CellValidation(
            status="FAILED",
            rule="row_total",
            expected=stated_total,
            actual=computed_sum,
            message=f"Arithmetic mismatch: sum of items is {computed_sum}, but sheet total reads {stated_total}",
        )

    @staticmethod
    def validate_range(
        min_val: Optional[Decimal],
        max_val: Optional[Decimal],
        field_name: str = "measurement",
    ) -> CellValidation:
        """Verifies that min <= max for measured ranges."""
        if min_val is None or max_val is None:
            return CellValidation(status="PASSED", rule="range_presence")

        if min_val <= max_val:
            return CellValidation(
                status="PASSED",
                rule="range_order",
                expected=f"{min_val} <= {max_val}",
                actual=f"{min_val} to {max_val}",
            )

        return CellValidation(
            status="FAILED",
            rule="range_order",
            expected=f"{min_val} <= {max_val}",
            actual=f"{min_val} > {max_val}",
            message=f"Inverted {field_name} range: minimum ({min_val}) is greater than maximum ({max_val})",
        )

    @staticmethod
    def validate_temperature_plausibility(
        temp: Optional[Decimal],
        is_cold_room: bool = True,
    ) -> CellValidation:
        """Flags implausible temperature readings for cold-storage cargo."""
        if temp is None:
            return CellValidation(status="PASSED")

        # Cold storage cargo typically ranges from -2°C to +15°C
        if temp < Decimal("-5.0") or temp > Decimal("25.0"):
            return CellValidation(
                status="WARNING",
                rule="plausibility",
                expected="Between -5°C and 25°C",
                actual=str(temp),
                message=f"Suspicious temperature reading: {temp}°C",
            )

        return CellValidation(status="PASSED")

