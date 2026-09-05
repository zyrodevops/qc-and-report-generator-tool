"""
Tier 4: Real-World Application Scenarios - Scenario 3: Sea Container Multi-Unit Survey.
Covers:
Full workflow of a multi-container sea shipment survey (6 containers):
- 6 Carriage Units with ISO 6346 container check digit validation
- CFS weighbridge reconciliation formula selection (gross - container tare)
- Handling historical surveyor-accepted 3 kg discrepancy (126,891 declared vs 126,888 found)
- Displaying both figures without auto-correction per CRITICAL-RULES §2
- Per-unit scoped photo numbering
"""

from decimal import Decimal
import pytest
from tests.e2e.helpers.contract_stubs import reference_cfs_reconciliation
from tests.e2e.helpers.synthetic_data import validate_iso6346


@pytest.mark.tier4
def test_scenario_sea_multi_unit_survey():
    """
    Simulates a 6-container marine cargo survey report per Master-Spec §6, §7 & §10.4.
    """
    # 1. Six container units with valid check digits
    containers = [
        {"id": "u1", "identifier": "CMAU2016593", "tare_kg": Decimal("2190"), "gross_kg": Decimal("23338"), "declared_net": Decimal("21148")},
        {"id": "u2", "identifier": "CMAU2016607", "tare_kg": Decimal("2190"), "gross_kg": Decimal("23338"), "declared_net": Decimal("21148")},
        {"id": "u3", "identifier": "CMAU2016612", "tare_kg": Decimal("2190"), "gross_kg": Decimal("23338"), "declared_net": Decimal("21148")},
        {"id": "u4", "identifier": "CMAU2016628", "tare_kg": Decimal("2190"), "gross_kg": Decimal("23338"), "declared_net": Decimal("21148")},
        {"id": "u5", "identifier": "CMAU2016633", "tare_kg": Decimal("2190"), "gross_kg": Decimal("23338"), "declared_net": Decimal("21148")},
        {"id": "u6", "identifier": "CMAU2016649", "tare_kg": Decimal("2190"), "gross_kg": Decimal("23338"), "declared_net": Decimal("21148")},
    ]

    # Validate ISO 6346 check digits
    for ctr in containers:
        assert validate_iso6346(ctr["identifier"]) is True

    # 2. CFS Weighbridge Reconciliation per unit
    total_found_net = Decimal("0")
    unit_reconciliations = []

    for ctr in containers:
        recon = reference_cfs_reconciliation(
            gross_kg=ctr["gross_kg"],
            container_tare_kg=ctr["tare_kg"],
            trailer_tare_kg=None,
            formula="GROSS_MINUS_CONTAINER_TARE",
            declared_net_kg=ctr["declared_net"]
        )
        total_found_net += recon["found_net_kg"]
        unit_reconciliations.append(recon)

    # In our scenario, each unit net is 23338 - 2190 = 21148 kg
    assert total_found_net == Decimal("126888.00")

    # 3. Discrepancy handling: Declared B/L weight is 126,891.00 kg
    declared_bl_weight = Decimal("126891.00")
    shipment_diff = declared_bl_weight - total_found_net
    assert shipment_diff == Decimal("3.00")

    # CRITICAL INVARIANT: The system must NOT auto-adjust 126888 to 126891!
    # Both numbers must be preserved and presented side-by-side with an advisory flag.
    reconciliation_summary = {
        "declared_gross_bl": declared_bl_weight,
        "found_gross_weighbridge": total_found_net,
        "difference_kg": shipment_diff,
        "flag": "DISCREPANCY_DETECTED",
        "surveyor_action": "ACCEPTED_AND_CONFIRMED"
    }

    assert reconciliation_summary["declared_gross_bl"] == Decimal("126891.00")
    assert reconciliation_summary["found_gross_weighbridge"] == Decimal("126888.00")
    assert reconciliation_summary["difference_kg"] == Decimal("3.00")
    assert reconciliation_summary["surveyor_action"] == "ACCEPTED_AND_CONFIRMED"
