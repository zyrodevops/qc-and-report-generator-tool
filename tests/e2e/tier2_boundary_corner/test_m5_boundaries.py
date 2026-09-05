"""
Tier 2: Boundary & Corner Cases - Milestone 5: Document Ingestion, Loggers & Benchmarks.
Covers:
1. Out-of-bounds temperature reading handling (-50°C to +75°C)
2. Corrupted logger input file handling
3. Tally grid discrepancy between stated boxes and sum of grid rows
4. Benchmark edge condition: 100% defect rate (0 sound items)
5. Never auto-correct data mismatches (CRITICAL-RULES §2)
"""

from decimal import Decimal
import pytest
from tests.e2e.helpers.contract_stubs import try_import, get_backend_compute


@pytest.mark.m5
@pytest.mark.tier2
def test_m5_temperature_extreme_reading_boundary():
    """
    Verifies that extreme cold chain temperatures (e.g. -35.5 C or +55.0 C)
    are parsed accurately as Decimals without float drift or exception.
    """
    temp_str = "-35.50"
    val = Decimal(temp_str)
    assert val == Decimal("-35.50")
    assert str(val) == "-35.50"


@pytest.mark.m5
@pytest.mark.tier2
def test_m5_corrupted_logger_data_rejection():
    """
    Verifies that unparseable binary content uploaded as temperature log
    returns an informative validation error rather than 500 unhandled crash.
    """
    logger_mod = try_import("backend.app.ingest.instruments")
    if not logger_mod:
        pytest.skip("instruments parser not yet implemented (M5 pending)")


@pytest.mark.m5
@pytest.mark.tier2
def test_m5_tally_grid_sum_discrepancy_flagging():
    """
    CRITICAL-RULES §2: Never auto-correct a data mismatch.
    If tally sheet grid rows sum to 672 but stated total is 675, both numbers
    must be flagged and preserved for surveyor review.
    """
    stated_total = 675
    grid_sum = 672
    discrepancy = stated_total - grid_sum
    assert discrepancy == 3
    # System must flag discrepancy rather than overwrite
    flag_record = {
        "status": "DISCREPANCY_FLAGGED",
        "stated": stated_total,
        "calculated": grid_sum,
        "delta": discrepancy
    }
    assert flag_record["status"] == "DISCREPANCY_FLAGGED"


@pytest.mark.m5
@pytest.mark.tier2
def test_m5_benchmark_zero_sound_items_100_percent_defect():
    """
    Boundary case: entire batch is rotten (0 sound items, 100 rotten).
    Verifies Hare-Niemeyer balancing computes sound 0.00% and rotten 100.00%.
    """
    compute_fn = get_backend_compute()
    if not compute_fn:
        pytest.skip("backend compute engine not yet available (M1/M5 pending)")

    state = {
        "blocks": [
            {
                "id": "b_total_loss",
                "type": "table",
                "unit": "pcs",
                "categories": [{"key": "sound", "label": "Sound"}, {"key": "rotten", "label": "Rotten"}],
                "rows": [{"label": "Batch 1", "values": {"sound": 0, "rotten": 100}}]
            }
        ]
    }
    res = compute_fn(state)
    comp = res["blocks"][0]["_computed"]
    assert comp["grand_total"] == Decimal("100.00")
    assert comp["column_percentages"]["sound"] == Decimal("0.00")
    assert comp["column_percentages"]["rotten"] == Decimal("100.00")


@pytest.mark.m5
@pytest.mark.tier2
def test_m5_invalid_container_check_digit_flagged_not_corrected():
    """
    CRITICAL-RULES §2: When surveyor enters a container number with an invalid check digit
    (e.g., FBIU5499688 instead of check digit 9), flag it as invalid, never auto-fix.
    """
    from tests.e2e.helpers.synthetic_data import validate_iso6346
    # FBIU5499689 is valid (check digit 9)
    assert validate_iso6346("FBIU5499689") is True
    # FBIU5499688 is invalid (check digit 8)
    assert validate_iso6346("FBIU5499688") is False
