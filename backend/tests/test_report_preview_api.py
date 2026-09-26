"""
API Integration Tests for Report Details and A4 HTML Preview Endpoints.
Covers:
- GET /api/reports/{id} (200, 400, 401, 404)
- GET /api/reports/{id}/preview/html (200 text/html, 400, 401, 404, query token)
"""

import uuid
from fastapi.testclient import TestClient
import pytest
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
    client.token = token
    return client


@pytest.fixture
def test_report(auth_client):
    state = make_synthetic_block_state(mode="SEA")
    res = auth_client.post(
        "/api/reports",
        json={
            "template_id": "perishable_qc_sea",
            "family": "QC_REPORT",
            "year": 2026,
            "block_state": state,
        },
    )
    assert res.status_code == 201
    return res.json()


# ---------------------------------------------------------------------------
# GET /api/reports/{id} Tests
# ---------------------------------------------------------------------------

def test_get_report_by_id_success(auth_client, test_report):
    report_id = test_report["id"]
    res = auth_client.get(f"/api/reports/{report_id}")
    assert res.status_code == 200
    assert res.headers["content-type"].startswith("application/json")

    data = res.json()
    assert data["id"] == report_id
    assert data["report_number"] == test_report["report_number"]
    assert data["family"] == "QC_REPORT"
    assert data["status"] == "DRAFT"
    assert data["version"] >= 1
    assert "block_state" in data
    assert len(data["block_state"]["blocks"]) == len(test_report["block_state"]["blocks"])


def test_get_report_by_id_not_found(auth_client):
    non_existent = str(uuid.uuid4())
    res = auth_client.get(f"/api/reports/{non_existent}")
    assert res.status_code == 404
    assert "not found" in res.json()["detail"].lower()


def test_get_report_by_id_invalid_uuid(auth_client):
    res = auth_client.get("/api/reports/not-a-valid-uuid-format")
    assert res.status_code == 400
    assert "invalid" in res.json()["detail"].lower()


def test_get_report_by_id_unauthorized(test_report):
    raw_client = TestClient(app)
    res = raw_client.get(f"/api/reports/{test_report['id']}")
    assert res.status_code == 401


# ---------------------------------------------------------------------------
# GET /api/reports/{id}/preview/html Tests
# ---------------------------------------------------------------------------

def test_get_report_preview_html_success(auth_client, test_report):
    report_id = test_report["id"]
    res = auth_client.get(f"/api/reports/{report_id}/preview/html")
    assert res.status_code == 200
    assert "text/html" in res.headers["content-type"]

    html_content = res.text
    assert "<!DOCTYPE html>" in html_content
    assert "a4-page" in html_content
    assert "PARTICULARS" in html_content
    assert "MEASUREMENTS" in html_content
    assert ">234<" in html_content  # pure compute table total, a whole count
    assert "56.84" in html_content   # Hare-Niemeyer balanced percentage


def test_get_report_preview_html_auth_via_query_token(test_report, auth_client):
    raw_client = TestClient(app)
    token = auth_client.token
    report_id = test_report["id"]
    res = raw_client.get(f"/api/reports/{report_id}/preview/html?auth_token={token}")
    assert res.status_code == 200
    assert "text/html" in res.headers["content-type"]


def test_get_report_preview_html_not_found(auth_client):
    non_existent = str(uuid.uuid4())
    res = auth_client.get(f"/api/reports/{non_existent}/preview/html")
    assert res.status_code == 404


def test_get_report_preview_html_invalid_uuid(auth_client):
    res = auth_client.get("/api/reports/not-a-uuid/preview/html")
    assert res.status_code == 400


def test_get_report_preview_html_unauthorized(test_report):
    raw_client = TestClient(app)
    res = raw_client.get(f"/api/reports/{test_report['id']}/preview/html")
    assert res.status_code == 401
