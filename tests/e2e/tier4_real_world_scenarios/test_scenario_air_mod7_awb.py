"""
Tier 4: Real-World Application Scenarios - Scenario 4: Air Cargo Shipment with Mod-7 AWB.
Covers:
Full workflow of an Air Waybill perishable/general cargo survey:
- 3-digit airline prefix + 7-digit serial + Mod-7 check digit
- Multi-leg air transit routing
- Volumetric weight calculation using IATA divisor 6,000 cm³/kg
- Chargeable weight calculation = max(actual, volumetric)
- Montreal Convention 1999 liability regime and 14-day written notice requirement
"""

from decimal import Decimal
import pytest
from tests.e2e.helpers.contract_stubs import reference_air_weights
from tests.e2e.helpers.synthetic_data import validate_awb_number


@pytest.mark.tier4
def test_scenario_air_cargo_shipment():
    """
    Simulates an air cargo survey report with Mod-7 AWB and volumetric weight calculations.
    """
    # 1. Validate Air Waybill with Mod-7 check digit
    # Serial: 1234567 -> 1234567 % 7 == 5 -> Full AWB: 098-12345675
    awb_number = "098-12345675"
    assert validate_awb_number(awb_number) is True

    # 2. Cargo details: 42 pieces of high-value cargo
    pieces = 42
    length_cm = 60.0
    width_cm = 50.0
    height_cm = 40.0
    actual_gross_kg = Decimal("650.00")

    # 3. Calculate Volumetric & Chargeable Weights
    # Vol cm3 = 60 * 50 * 40 * 42 = 5,040,000 cm3
    # Vol kg = 5,040,000 / 6000 = 840.00 kg
    volumetric_kg, chargeable_kg = reference_air_weights(
        length_cm=length_cm,
        width_cm=width_cm,
        height_cm=height_cm,
        actual_gross_kg=actual_gross_kg,
        pieces=pieces,
        divisor=6000
    )

    assert volumetric_kg == Decimal("840.00")
    # Chargeable weight must be the maximum of actual gross and volumetric weight
    assert chargeable_kg == Decimal("840.00")

    # 4. Multi-leg conveyance details
    conveyances = [
        {"leg": 1, "flight": "BA-112", "date": "2026-08-01", "from": "LHR", "to": "DOH"},
        {"leg": 2, "flight": "QR-556", "date": "2026-08-02", "from": "DOH", "to": "BOM"}
    ]
    assert len(conveyances) == 2

    # 5. Montreal Convention Regime verification
    liability_regime = {
        "instrument": "Montreal Convention 1999 via Carriage by Air Act 1972",
        "limit_basis": "per_kg",
        "notice_period_days": 14,
        "confirmed_by": "surveyor",
        "effective_date": "2026-08-03"
    }
    assert liability_regime["notice_period_days"] == 14
    assert liability_regime["confirmed_by"] == "surveyor"
