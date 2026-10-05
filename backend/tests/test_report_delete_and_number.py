"""
Tests for Report Deletion, Custom Report Numbers, and Sequence Reset.
"""

import os
import uuid
import pytest
from fastapi.testclient import TestClient
from app.main import app
from tests.e2e.helpers.synthetic_data import make_synthetic_block_state


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


def test_create_report_with_custom_number(auth_client):
    unique_num = f"M-TEST-{uuid.uuid4().hex[:6].upper()}-2026"
    res = auth_client.post(
        "/api/reports",
        json={
            "template_id": "perishable_qc_sea",
            "family": "QC_REPORT",
            "year": 2026,
            "custom_report_number": unique_num,
            "block_state": make_synthetic_block_state(mode="SEA"),
        },
    )
    assert res.status_code == 201
    data = res.json()
    assert data["report_number"] == unique_num
    assert data["block_state"]["metadata"]["number"] == unique_num

    # Trying to reuse same report number must fail with 400
    dup_res = auth_client.post(
        "/api/reports",
        json={
            "template_id": "perishable_qc_sea",
            "family": "QC_REPORT",
            "year": 2026,
            "custom_report_number": unique_num,
            "block_state": make_synthetic_block_state(mode="SEA"),
        },
    )
    assert dup_res.status_code == 400
    assert "already in use" in dup_res.json()["detail"].lower()

    # Clean up
    del_res = auth_client.delete(f"/api/reports/{data['id']}")
    assert del_res.status_code == 200


def test_delete_report_success(auth_client):
    # 1. Create a draft report
    res = auth_client.post(
        "/api/reports",
        json={
            "template_id": "perishable_qc_sea",
            "family": "QC_REPORT",
            "year": 2026,
            "block_state": make_synthetic_block_state(mode="SEA"),
        },
    )
    assert res.status_code == 201
    report_id = res.json()["id"]

    # 2. Delete it
    del_res = auth_client.delete(f"/api/reports/{report_id}")
    assert del_res.status_code == 200
    del_data = del_res.json()
    assert del_data["success"] is True
    assert del_data["id"] == report_id

    # 3. Confirm 404 on fetch
    get_res = auth_client.get(f"/api/reports/{report_id}")
    assert get_res.status_code == 404


def test_delete_report_not_found(auth_client):
    random_id = str(uuid.uuid4())
    del_res = auth_client.delete(f"/api/reports/{random_id}")
    assert del_res.status_code == 404


def test_delete_report_invalid_uuid(auth_client):
    del_res = auth_client.delete("/api/reports/invalid-uuid-string")
    assert del_res.status_code == 400


def test_reset_sequence(auth_client):
    import random
    test_year = random.randint(2080, 2090)
    res = auth_client.post(
        "/api/reports/sequence/reset",
        json={"year": test_year, "next_val": 42},
    )
    assert res.status_code == 200
    assert res.json()["next_report_number"] == f"M-42-{test_year}"

    # Allocate next report in that test year without custom number
    create_res = auth_client.post(
        "/api/reports",
        json={
            "template_id": "perishable_qc_sea",
            "family": "QC_REPORT",
            "year": test_year,
            "block_state": make_synthetic_block_state(mode="SEA"),
        },
    )
    assert create_res.status_code == 201
    assert create_res.json()["report_number"] == f"M-42-{test_year}"

    # Clean up test report
    auth_client.delete(f"/api/reports/{create_res.json()['id']}")


# The tests run against the app's own database, so "Delete All" here deletes
# every real report too (it did once). Run it only on purpose, on a scratch
# database: ALLOW_DELETE_ALL_TEST=1 pytest tests/test_report_delete_and_number.py
@pytest.mark.skipif(
    os.getenv("ALLOW_DELETE_ALL_TEST") != "1",
    reason="deletes every report in the database; set ALLOW_DELETE_ALL_TEST=1 on a scratch database",
)
def test_delete_all_reports(auth_client):
    # 1. Create two test reports
    r1 = auth_client.post(
        "/api/reports",
        json={
            "template_id": "perishable_qc_sea",
            "family": "QC_REPORT",
            "year": 2026,
            "block_state": make_synthetic_block_state(mode="SEA"),
        },
    )
    assert r1.status_code == 201

    r2 = auth_client.post(
        "/api/reports",
        json={
            "template_id": "perishable_qc_sea",
            "family": "QC_REPORT",
            "year": 2026,
            "block_state": make_synthetic_block_state(mode="SEA"),
        },
    )
    assert r2.status_code == 201

    # 2. Call DELETE /api/reports/all
    del_all = auth_client.delete("/api/reports/all")
    assert del_all.status_code == 200
    assert del_all.json()["success"] is True
    assert del_all.json()["deleted_count"] >= 2

    # 3. Verify GET /api/reports returns empty list
    list_res = auth_client.get("/api/reports")
    assert list_res.status_code == 200
    assert len(list_res.json()) == 0

