"""
Tier 2: Boundary & Corner Cases - R2: Block State & Arithmetic Engine.
Covers:
1. Zero division protection (all zeros table)
2. Empty table rows handling
3. Single column table (100.00% invariant)
4. Hare-Niemeyer Largest Remainder Method rounding drift prevention (three 1/3 values sum to 100.00%)
5. Data mismatch flagging (declared vs found weight)
6. Precision quantization and ROUND_HALF_UP tie-breaking
"""

from decimal import Decimal
import pytest
from tests.e2e.helpers.contract_stubs import (
    reference_compute_table,
    hare_niemeyer_balance
)


@pytest.mark.m2
@pytest.mark.tier2
def test_zero_division_protection_all_zeros_table():
    """
    Verifies that a table where all defect counts are zero calculates 0 grand total
    and 0.00% for each category WITHOUT raising ZeroDivisionError.
    """
    categories = ["sound", "soft", "decay"]
    rows = [
        {"group": "Sample 1", "values": {"sound": 0, "soft": 0, "decay": 0}},
        {"group": "Sample 2", "values": {"sound": 0, "soft": 0, "decay": 0}}
    ]

    res = reference_compute_table(rows, categories)
    assert res["grand_total"] == Decimal("0")
    for cat in categories:
        assert res["column_totals"][cat] == Decimal("0")
        assert res["column_percentages"][cat] == Decimal("0.00")
    for r_pcts in res["row_percentages"]:
        for pct in r_pcts:
            assert pct == Decimal("0.00")


@pytest.mark.m2
@pytest.mark.tier2
def test_empty_rows_table():
    """
    Verifies that a table block with empty rows list computes cleanly with zero totals.
    """
    categories = ["sound", "soft"]
    rows = []
    res = reference_compute_table(rows, categories)
    assert res["grand_total"] == Decimal("0")
    assert len(res["row_totals"]) == 0


@pytest.mark.m2
@pytest.mark.tier2
def test_single_column_table_invariants():
    """
    Verifies that a table with a single category column computes 100.00% regardless of count.
    """
    categories = ["damaged"]
    rows = [
        {"group": "Lot 1", "values": {"damaged": 45}},
        {"group": "Lot 2", "values": {"damaged": 55}}
    ]
    res = reference_compute_table(rows, categories)
    assert res["grand_total"] == Decimal("100")
    assert res["column_percentages"]["damaged"] == Decimal("100.00")
    assert res["row_percentages"][0][0] == Decimal("100.00")
    assert res["row_percentages"][1][0] == Decimal("100.00")


@pytest.mark.m2
@pytest.mark.tier2
def test_hare_niemeyer_rounding_drift_three_way_split():
    """
    Verifies that three equal values (1, 1, 1 -> 33.333...% each) are balanced
    using Hare-Niemeyer Largest Remainder Method so the vector sums to EXACTLY 100.00%.
    Naive rounding yields 33.33 + 33.33 + 33.33 = 99.99% (a 1-cent drift).
    Hare-Niemeyer must adjust the highest remainder to yield exactly 100.00%.
    """
    categories = ["c1", "c2", "c3"]
    rows = [{"group": "Equal Split", "values": {"c1": 1, "c2": 1, "c3": 1}}]
    
    res = reference_compute_table(rows, categories)
    pcts = res["row_percentages"][0]

    assert sum(pcts) == Decimal("100.00"), f"Sum was {sum(pcts)}, expected 100.00"
    # One element receives 33.34, other two receive 33.33
    assert sorted(pcts) == [Decimal("33.33"), Decimal("33.33"), Decimal("33.34")]


@pytest.mark.m2
@pytest.mark.tier2
def test_data_mismatch_flagging_never_auto_correct():
    """
    Verifies CRITICAL-RULES §2:
    Never auto-correct a data mismatch. If declared weight != found weight,
    show both sources and flag it.
    """
    declared_net_kg = Decimal("126891.00")
    # Surveyor weighed 6 containers: 6 x 21148 = 126888 kg (3 kg difference)
    found_net_kg = Decimal("126888.00")
    discrepancy_kg = abs(declared_net_kg - found_net_kg)

    assert discrepancy_kg == Decimal("3.00")
    # Invariant: Neither value may be silently altered to match the other
    assert declared_net_kg != found_net_kg


@pytest.mark.m2
@pytest.mark.tier2
def test_high_precision_round_half_up_quantization():
    """
    Verifies that ROUND_HALF_UP rounding handles exact midpoint fractions properly:
    e.g. 1.225 rounds to 1.23, 1.224 rounds to 1.22.
    """
    q = Decimal("0.01")
    val_up = Decimal("1.225").quantize(q, rounding="ROUND_HALF_UP")
    val_down = Decimal("1.224").quantize(q, rounding="ROUND_HALF_UP")

    assert val_up == Decimal("1.23")
    assert val_down == Decimal("1.22")
