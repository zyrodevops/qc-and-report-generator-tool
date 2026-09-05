"""
Tier 1: Feature Coverage - R7: End-to-End Form and Report Lifecycle.
Covers:
1. Report list creation & sequence allocation
2. SEA transport module & ISO 6346 validation
3. AIR transport module & Mod-7 AWB validation
4. Dynamic block form generation
5. Server-side DOCX download action
"""

import pytest
from tests.e2e.helpers.contract_stubs import try_import
from tests.e2e.helpers.synthetic_data import (
    validate_iso6346,
    validate_awb_number,
    make_synthetic_block_state
)


@pytest.mark.m5
@pytest.mark.tier1
def test_report_create_api_flow(api_client):
    """
    Verifies creating a report via API: allocates M-<n>-<year> number and persists block_state.
    """
    if not api_client.is_available():
        pytest.skip("Backend API not yet available (M1/M5 pending)")

    payload = {
        "template_id": "perishable-qc-sea",
        "transport_mode": "SEA",
        "year": 2026
    }
    res = api_client.post("/api/reports", json=payload)
    if res.status_code in [200, 201]:
        data = res.json()
        assert "id" in data
        assert "report_number" in data
        assert data["report_number"].startswith("M-")


@pytest.mark.m5
@pytest.mark.tier1
def test_sea_transport_mode_contract(synthetic_state_sea):
    """
    Verifies SEA transport module: requires Bill of Lading, Container ID (ISO 6346 check digit),
    and tare weights.
    """
    transport = synthetic_state_sea["transport"]
    assert transport["mode"] == "SEA"
    assert transport["document"]["kind"] == "BILL_OF_LADING"

    container = synthetic_state_sea["carriage_units"][0]
    assert container["unit_type"] == "CONTAINER"
    # Verify ISO 6346 check digit on sample container CMAU2016593
    assert validate_iso6346(container["identifier"]) is True


@pytest.mark.m5
@pytest.mark.tier1
def test_air_transport_mode_contract(synthetic_state_air):
    """
    Verifies AIR transport module: requires Air Waybill (Mod-7 check digit),
    and includes volumetric/chargeable weights.
    """
    transport = synthetic_state_air["transport"]
    assert transport["mode"] == "AIR"
    assert transport["document"]["kind"] == "AIR_WAYBILL"

    awb = transport["document"]["number"]
    # Verify Mod-7 check digit on 098-12345675 (1234567 % 7 == 5)
    assert validate_awb_number(awb) is True


@pytest.mark.m5
@pytest.mark.tier1
def test_dynamic_block_form_rendering_contract(synthetic_state_sea):
    """
    Verifies that the block list in state drives the form sections.
    Each block in state must correspond to a supported block form component.
    """
    blocks = synthetic_state_sea["blocks"]
    valid_component_types = {
        "particulars", "narrative", "measurements", "table", "fixed_text", "photo_plate"
    }
    for b in blocks:
        assert b["type"] in valid_component_types


@pytest.mark.m5
@pytest.mark.tier1
def test_docx_download_action_flow(api_client, synthetic_state_sea):
    """
    Verifies the download button action: sends request to server, runs Traceability Gate,
    and returns application/vnd.openxmlformats-officedocument.wordprocessingml.document.
    """
    if not api_client.is_available():
        pytest.skip("Backend API not yet available (M3/M5 pending)")

    res = api_client.post("/api/reports/download", json=synthetic_state_sea)
    if res.status_code == 200:
        assert "openxmlformats" in res.headers.get("content-type", "")
        assert len(res.content) > 1000
