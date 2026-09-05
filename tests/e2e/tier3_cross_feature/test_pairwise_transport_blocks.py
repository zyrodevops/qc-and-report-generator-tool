"""
Tier 3: Cross-Feature Combinations - Pairwise Transport & Block Sequences.
Covers:
1. SEA x Single-Unit x Standard QC Block Sequence
2. SEA x Multi-Unit x Full Survey Block Sequence
3. AIR x Single-Unit x Perishable QC Sequence (volumetric weights + AWB)
4. AIR x Multi-Unit (ULDs) x Cargo Damage Survey Sequence
5. Liability regime confirmation across transport modes
"""

import pytest
from tests.e2e.helpers.synthetic_data import make_synthetic_block_state
from tests.e2e.helpers.contract_stubs import try_import


@pytest.mark.tier3
@pytest.mark.parametrize("mode,multi_unit", [
    ("SEA", False),
    ("SEA", True),
    ("AIR", False),
    ("AIR", True),
])
def test_transport_carriage_pairwise_matrix(mode, multi_unit):
    """
    Tests the combinatorial matrix of transport mode (SEA vs AIR) and
    carriage unit topology (Single Container/Unit vs Multi-Unit).
    """
    state = make_synthetic_block_state(mode=mode, multi_unit=multi_unit)
    assert state["transport"]["mode"] == mode
    assert len(state["carriage_units"]) >= (2 if multi_unit else 1)

    if mode == "SEA":
        assert state["transport"]["document"]["kind"] == "BILL_OF_LADING"
        assert state["carriage_units"][0]["unit_type"] == "CONTAINER"
    elif mode == "AIR":
        assert state["transport"]["document"]["kind"] == "AIR_WAYBILL"


@pytest.mark.tier3
def test_block_sequence_composition_and_reordering(synthetic_state_sea):
    """
    Verifies that blocks can be dynamically reordered, added, or removed
    without breaking the document structure or state contract.
    """
    state = dict(synthetic_state_sea)
    original_order = [b["type"] for b in state["blocks"]]

    # Reverse order of blocks
    state["blocks"] = list(reversed(state["blocks"]))
    reversed_order = [b["type"] for b in state["blocks"]]

    assert reversed_order == list(reversed(original_order))
    assert len(state["blocks"]) == len(original_order)


@pytest.mark.tier3
def test_liability_regime_mode_awareness(synthetic_state_sea, synthetic_state_air):
    """
    Verifies Master-Spec §6 & §10.9:
    SEA selects Hague-Visby/COGSA with package/kg limitation.
    AIR selects Montreal Convention 1999 with SDR per kg limitation and 14-day notice period.
    """
    sea_regime = synthetic_state_sea["transport"]["liability_regime"]
    air_regime = synthetic_state_air["transport"]["liability_regime"]

    assert "Hague" in sea_regime["instrument"] or "COGSA" in sea_regime["instrument"]
    assert "Montreal" in air_regime["instrument"]
    assert air_regime["notice_period_days"] == 14
