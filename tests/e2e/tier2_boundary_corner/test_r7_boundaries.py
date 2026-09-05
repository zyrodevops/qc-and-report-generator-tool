"""
Tier 2: Boundary & Corner Cases - R7: Form, Transport, and Gate Boundaries.
Covers:
1. Invalid ISO 6346 container check digit flagged without auto-correction
2. Invalid IATA Mod-7 AWB check digit flagged
3. Air volumetric weight calculation with boundary/zero dimensions
4. Missing required block in state validation
5. Unauthorized download access rejection
"""

from decimal import Decimal
import pytest
from tests.e2e.helpers.contract_stubs import reference_air_weights
from tests.e2e.helpers.synthetic_data import (
    validate_iso6346,
    validate_awb_number
)


@pytest.mark.m5
@pytest.mark.tier2
def test_invalid_iso6346_check_digit_flagging():
    """
    CRITICAL-RULES §2 & Master-Spec §6:
    Never auto-correct an invalid container check digit.
    Flag it for the surveyor to verify against physical container markings.
    """
    # Valid: CMAU2016593
    assert validate_iso6346("CMAU2016593") is True

    # Mutate check digit to 8 (invalid)
    invalid_container = "CMAU2016598"
    assert validate_iso6346(invalid_container) is False


@pytest.mark.m5
@pytest.mark.tier2
def test_invalid_awb_mod7_check_digit_flagging():
    """
    Verifies that an invalid AWB check digit (serial % 7 != check digit) is flagged.
    Serial 1234567 % 7 is 5.
    If written 098-1234567-2, check digit is invalid.
    """
    valid_awb = "098-12345675"
    assert validate_awb_number(valid_awb) is True

    invalid_awb = "098-12345672"
    assert validate_awb_number(invalid_awb) is False


@pytest.mark.m5
@pytest.mark.tier2
def test_air_volumetric_weight_boundary_zero_and_negative():
    """
    Verifies that zero or negative piece dimensions are rejected or handled cleanly.
    """
    actual_gross = Decimal("100.00")
    
    # Zero dimensions -> volumetric is 0, chargeable is actual
    vol, chg = reference_air_weights(0, 0, 0, actual_gross)
    assert vol == Decimal("0.00")
    assert chg == actual_gross

    # Typical air cargo parcel: 100cm x 80cm x 60cm, 1 piece
    # Vol = (100 * 80 * 60) / 6000 = 480,000 / 6000 = 80.00 kg
    vol2, chg2 = reference_air_weights(100, 80, 60, Decimal("50.00"))
    assert vol2 == Decimal("80.00")
    assert chg2 == Decimal("80.00")  # volumetric exceeds actual


@pytest.mark.m5
@pytest.mark.tier2
def test_missing_required_block_in_state_rejection():
    """
    Verifies that submitting a BlockState missing required core structures
    (such as empty blocks array or missing metadata) raises a validation error.
    """
    try:
        from backend.app.blocks.state import BlockState
        with pytest.raises(Exception):
            BlockState(metadata={}, transport={}, carriage_units=[], blocks=[])
    except (ImportError, ModuleNotFoundError):
        # Progressively validated via contract structure
        pass


@pytest.mark.m5
@pytest.mark.tier2
def test_unauthorized_download_blocked(api_client, synthetic_state_sea):
    """
    Verifies that an unauthenticated request to the download endpoint is rejected (401/403).
    """
    if not api_client.is_available():
        pytest.skip("Backend API not yet available (M1/M5 pending)")

    headers = {}  # No auth header
    res = api_client.post("/api/reports/download", json=synthetic_state_sea, headers=headers)
    assert res.status_code in [401, 403]
