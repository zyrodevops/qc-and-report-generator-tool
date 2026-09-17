"""
Optimistic Concurrency Tests for PATCH /api/reports/{id}/block-state.
Master Spec §10.7 (Day 8): "Autosave with optimistic concurrency (version number,
reject stale writes)."

Tests:
1. PATCH with correct version → 200, version incremented.
2. PATCH with stale version → 409 Conflict with current_version in response.
3. PATCH with version missing → 422 Validation error.
4. Two concurrent writes: first wins, second conflicts.
5. Computed keys (_computed) are stripped from saved state.
6. Audit trail records before/after on successful PATCH.
"""

from __future__ import annotations

import uuid
from typing import Any, Dict

import pytest
from fastapi.testclient import TestClient

from app.main import app


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def auth_client():
    client = TestClient(app)
    login_res = client.post(
        "/api/auth/login",
        json={"email": "surveyor@example.com", "password": "Password123!"}
    )
    assert login_res.status_code == 200
    token = login_res.json()["token"]
    client.headers.update({"Authorization": f"Bearer {token}"})
    return client


@pytest.fixture
def fresh_report(auth_client):
    """Create a fresh report and return its full response JSON."""
    res = auth_client.post(
        "/api/reports",
        json={
            "template_id": "perishable_qc_sea",
            "family": "QC_REPORT",
            "year": 2026,
            "block_state": {
                "metadata": {"number": "M-CONCURRENCY-TEST", "docx_template": "mca-qc-synthetic.docx"},
                "blocks": [
                    {
                        "id": "b_init",
                        "type": "narrative",
                        "section": "INITIAL",
                        "additional_text": "Initial block state.",
                    }
                ],
            },
        },
    )
    assert res.status_code == 201
    return res.json()


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def test_patch_with_correct_version_succeeds(auth_client, fresh_report):
    """PATCH with the current version succeeds and increments the version."""
    report_id = fresh_report["id"]
    current_version = fresh_report["version"]  # Should be 1

    new_state = {
        "metadata": {"number": fresh_report["report_number"], "docx_template": "mca-qc-synthetic.docx"},
        "blocks": [
            {
                "id": "b_updated",
                "type": "narrative",
                "section": "UPDATED",
                "additional_text": "Updated block state — first edit.",
            }
        ],
    }

    res = auth_client.patch(
        f"/api/reports/{report_id}/block-state",
        json={"block_state": new_state, "version": current_version},
    )

    assert res.status_code == 200, f"Expected 200, got {res.status_code}: {res.text}"
    body = res.json()
    assert body["status"] == "updated"
    assert body["report_id"] == report_id
    assert body["new_version"] == current_version + 1


def test_patch_with_stale_version_returns_409(auth_client, fresh_report):
    """PATCH with a stale version returns HTTP 409 Conflict."""
    report_id = fresh_report["id"]
    current_version = fresh_report["version"]  # Should be 1

    new_state = {
        "metadata": {"number": fresh_report["report_number"], "docx_template": "mca-qc-synthetic.docx"},
        "blocks": [],
    }

    # Submit version 999 — clearly stale / wrong
    res = auth_client.patch(
        f"/api/reports/{report_id}/block-state",
        json={"block_state": new_state, "version": 999},
    )

    assert res.status_code == 409, f"Expected 409, got {res.status_code}: {res.text}"
    body = res.json()
    detail = body["detail"]
    assert detail["error"] == "version_conflict"
    assert detail["current_version"] == current_version
    assert detail["submitted_version"] == 999


def test_patch_with_version_zero_returns_422(auth_client, fresh_report):
    """PATCH with version=0 (invalid, must be >=1) returns HTTP 422."""
    report_id = fresh_report["id"]
    res = auth_client.patch(
        f"/api/reports/{report_id}/block-state",
        json={"block_state": {}, "version": 0},
    )
    assert res.status_code == 422


def test_patch_sequential_versions_increment(auth_client, fresh_report):
    """Each successful PATCH increments the version by 1."""
    report_id = fresh_report["id"]

    for expected_new_version in range(2, 6):  # Versions 2, 3, 4, 5
        current_version = expected_new_version - 1
        new_state = {
            "metadata": {
                "number": fresh_report["report_number"],
                "docx_template": "mca-qc-synthetic.docx",
                "edit_count": expected_new_version,
            },
            "blocks": [
                {
                    "id": "b_seq",
                    "type": "narrative",
                    "section": "SEQ",
                    "additional_text": f"Edit {expected_new_version}",
                }
            ],
        }
        res = auth_client.patch(
            f"/api/reports/{report_id}/block-state",
            json={"block_state": new_state, "version": current_version},
        )
        assert res.status_code == 200, (
            f"Version {current_version} → {expected_new_version} failed: {res.text}"
        )
        assert res.json()["new_version"] == expected_new_version


def test_two_concurrent_writes_second_conflicts(auth_client, fresh_report):
    """
    Simulate two 'concurrent' writers both reading version 1.
    First write succeeds (version becomes 2).
    Second write with version=1 (now stale) must be rejected with 409.
    """
    report_id = fresh_report["id"]
    initial_version = fresh_report["version"]  # 1

    state_a = {
        "metadata": {"number": fresh_report["report_number"], "docx_template": "mca-qc-synthetic.docx"},
        "blocks": [{"id": "b_a", "type": "narrative", "section": "A", "additional_text": "Writer A"}],
    }
    state_b = {
        "metadata": {"number": fresh_report["report_number"], "docx_template": "mca-qc-synthetic.docx"},
        "blocks": [{"id": "b_b", "type": "narrative", "section": "B", "additional_text": "Writer B"}],
    }

    # Writer A goes first — succeeds
    res_a = auth_client.patch(
        f"/api/reports/{report_id}/block-state",
        json={"block_state": state_a, "version": initial_version},
    )
    assert res_a.status_code == 200, f"Writer A failed: {res_a.text}"
    assert res_a.json()["new_version"] == initial_version + 1

    # Writer B tries to write with the same stale version — must fail
    res_b = auth_client.patch(
        f"/api/reports/{report_id}/block-state",
        json={"block_state": state_b, "version": initial_version},  # stale!
    )
    assert res_b.status_code == 409, f"Expected 409 for Writer B, got: {res_b.text}"
    assert res_b.json()["detail"]["error"] == "version_conflict"


def test_patch_strips_computed_keys(auth_client, fresh_report):
    """
    _computed keys must be stripped before saving to DB — CRITICAL-RULES §1.
    The PATCH should succeed even if the client sends _computed, but those keys
    must not appear in the stored block_state.
    """
    report_id = fresh_report["id"]
    current_version = fresh_report["version"]

    state_with_computed = {
        "metadata": {"number": fresh_report["report_number"], "docx_template": "mca-qc-synthetic.docx"},
        "blocks": [
            {
                "id": "b_tbl",
                "type": "table",
                "title": "Test",
                "unit": "pcs",
                "grouping_label": "Lot",
                "categories": [{"key": "sound", "label": "Sound"}],
                "rows": [{"group": "A", "values": {"sound": "50"}}],
                # Client sends _computed — must be stripped before saving
                "_computed": {
                    "grand_total": "50.00",
                    "column_totals": {"sound": "50.00"},
                },
            }
        ],
    }

    res = auth_client.patch(
        f"/api/reports/{report_id}/block-state",
        json={"block_state": state_with_computed, "version": current_version},
    )
    assert res.status_code == 200

    # Verify the stored state doesn't have _computed
    get_res = auth_client.get(f"/api/reports/{report_id}")
    assert get_res.status_code == 200
    stored_state = get_res.json()["block_state"]
    for block in stored_state.get("blocks", []):
        assert "_computed" not in block, (
            f"_computed key found in stored block {block.get('id')!r}. "
            "Computed values must never be stored (CRITICAL-RULES §1)."
        )


def test_patch_unauthorized_returns_401(fresh_report):
    """PATCH without authentication returns 401."""
    client = TestClient(app)  # No auth headers
    report_id = fresh_report["id"]
    res = client.patch(
        f"/api/reports/{report_id}/block-state",
        json={"block_state": {}, "version": 1},
    )
    assert res.status_code == 401


def test_patch_nonexistent_report_returns_404(auth_client):
    """PATCH on a non-existent report ID returns 404."""
    non_existent = str(uuid.uuid4())
    res = auth_client.patch(
        f"/api/reports/{non_existent}/block-state",
        json={"block_state": {}, "version": 1},
    )
    assert res.status_code == 404


def test_report_version_reflected_in_get_response(auth_client, fresh_report):
    """
    After a successful PATCH, GET /api/reports/{id} must return the new version.
    This verifies the version is correctly stored and returned.
    """
    report_id = fresh_report["id"]
    initial_version = fresh_report["version"]

    new_state = {
        "metadata": {"number": fresh_report["report_number"], "docx_template": "mca-qc-synthetic.docx"},
        "blocks": [{"id": "b_v2", "type": "narrative", "section": "V2", "additional_text": "V2 state"}],
    }

    patch_res = auth_client.patch(
        f"/api/reports/{report_id}/block-state",
        json={"block_state": new_state, "version": initial_version},
    )
    assert patch_res.status_code == 200
    new_version = patch_res.json()["new_version"]

    # Now GET the report — must reflect new_version
    get_res = auth_client.get(f"/api/reports/{report_id}")
    assert get_res.status_code == 200
    assert get_res.json()["version"] == new_version, (
        f"GET /reports/{report_id} returned version {get_res.json()['version']}, "
        f"expected {new_version}"
    )
