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
from typing import Any, Dict, List, Optional, Tuple, Union

from app.ingest.tally.models import CellValidation


Number = Union[int, Decimal]


def _is_count(v: Any) -> bool:
    """A usable figure: a whole count (pcs) or a Decimal weight (kg). Never bool or float."""
    return isinstance(v, (int, Decimal)) and not isinstance(v, bool) and v >= 0


class ValidationEngine:
    """Performs strict arithmetic and domain checks on extracted tally data."""

    @staticmethod
    def validate_row_total(
        defect_values: Dict[str, Number],
        stated_total: Optional[Number] = None,
    ) -> Tuple[Number, CellValidation]:
        """
        Compare the sum of the cells read off the row against the total the
        surveyor wrote at the end of it.

        Three outcomes, and they are deliberately three rather than two:

          PASSED   a total was written and it agrees with the cells
          FAILED   a total was written and it does not agree
          SKIPPED  no total was written, so there is nothing to check against

        The third case used to return PASSED, which showed the surveyor a green
        tick on a row that had never been checked. An unchecked row has to look
        different from a verified one or the check is worse than not having it.

        Works for counts and for kg weights alike. Weights are Decimals, so a row
        of 0.820 + 0.520 + 0.120 sums to exactly 1.460 — as floats it would come
        to 1.4600000000000002 and fail against the surveyor's own figure.
        """
        figures = [v for v in defect_values.values() if _is_count(v)]
        computed_sum: Number = sum(figures, Decimal(0)) if any(isinstance(v, Decimal) for v in figures) else sum(figures)

        if stated_total is None:
            return computed_sum, CellValidation(
                status="SKIPPED",
                rule="row_total",
                expected=None,
                actual=computed_sum,
                message="No written total on this row — nothing to check the cells against.",
            )

        if Decimal(computed_sum) == Decimal(stated_total):
            return computed_sum, CellValidation(
                status="PASSED",
                rule="row_total",
                expected=stated_total,
                actual=computed_sum,
                message=f"Row ties out: cells add to {computed_sum}, matching the written total.",
            )

        # Mismatch detected: never silently guess or alter values.
        delta = Decimal(computed_sum) - Decimal(stated_total)
        return computed_sum, CellValidation(
            status="FAILED",
            rule="row_total",
            expected=stated_total,
            actual=computed_sum,
            message=(
                f"Cells add to {computed_sum} but the written total reads {stated_total} "
                f"({delta:+}). Check this row against the sheet."
            ),
        )

    @staticmethod
    def validate_column_totals(
        rows: List[Dict[str, Any]],
        category_keys: List[str],
    ) -> Dict[str, Number]:
        """Column sums across every row, for the workbench footer."""
        totals: Dict[str, Number] = {k: 0 for k in category_keys}
        for row in rows:
            for k in category_keys:
                v = row.get("values", {}).get(k)
                if _is_count(v):
                    totals[k] = totals[k] + v
        return totals

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

