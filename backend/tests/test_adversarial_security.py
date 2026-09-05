"""
Adversarial Security, Error Handling, and XSS Sanitization Test Suite for Milestone 1.

Verifies:
1. XSS injection across all block types (narrative, table, particulars, measurements, photo_plate, fixed_text).
2. Endpoint error cases for GET /api/reports/{id} and GET /api/reports/{id}/preview/html:
   - Malformed UUIDs (400)
   - Non-existent UUIDs (404)
   - Unauthorized requests without token (401)
   - Expired and corrupted session tokens (401)
   - Dual transport and query parameter token authentication (200 / 401)
3. Strict HTTP status codes and Content-Type header enforcement.
4. Adversarial edge cases: Local File Inclusion (LFI) via asset paths, None-value handling, Unicode.
"""

import asyncio
import base64
import json
import time
import uuid
from typing import Any, Dict

from bs4 import BeautifulSoup
from fastapi.testclient import TestClient
import pytest

from app.main import app
from app.redis_client import get_redis_client
from app.render.html.engine import render_html


@pytest.fixture
def test_client():
    return TestClient(app)


@pytest.fixture
def auth_session(test_client):
    """Authenticate and return client with valid Bearer token and raw token string."""
    res = test_client.post(
        "/api/auth/login",
        json={"email": "surveyor@example.com", "password": "Password123!"},
    )
    assert res.status_code == 200, f"Login failed: {res.text}"
    token = res.json()["token"]
    test_client.headers.update({"Authorization": f"Bearer {token}"})
    return test_client, token


@pytest.fixture
def sample_report_id(auth_session):
    client, _ = auth_session
    payload = {
        "template_id": "perishable-qc-sea",
        "family": "marine_cargo",
        "year": 2026,
        "block_state": {
            "metadata": {"number": "M-2026-ADV-01"},
            "blocks": [
                {
                    "id": "b_narr",
                    "type": "narrative",
                    "section": "ATTENDANCE & CIRCUMSTANCES",
                    "content": "Survey completed normally without exceptions.",
                },
                {
                    "id": "b_tbl",
                    "type": "table",
                    "title": "DEFECT ANALYSIS",
                    "unit": "pcs",
                    "grouping_label": "Carton Lot",
                    "categories": [
                        {"key": "sound", "label": "Sound"},
                        {"key": "bruised", "label": "Bruised"},
                    ],
                    "rows": [
                        {"group": "Lot 1", "values": {"sound": 80, "bruised": 20}}
                    ],
                },
            ],
        },
    }
    res = client.post("/api/reports", json=payload)
    assert res.status_code == 201, f"Report creation failed: {res.text}"
    return res.json()["id"]


# ===========================================================================
# 1. XSS Injection & HTML Escaping Verification
# ===========================================================================

def test_xss_narrative_block_script_tags():
    """Ensure <script> tags in narrative content/additional_text are escaped and not executable."""
    state = {
        "metadata": {"number": "M-2026-XSS-NARR"},
        "blocks": [
            {
                "id": "b_narr1",
                "type": "narrative",
                "section": "<script>alert('xss-sec')</script>",
                "content": "<script>alert('xss-content')</script>",
                "additional_text": "<script src='https://evil.example.com/payload.js'></script>",
            }
        ],
    }
    rendered = render_html(state)
    soup = BeautifulSoup(rendered, "html.parser")

    assert len(soup.find_all("script")) == 0, "Script tag parsed in DOM"
    assert "<script>" not in rendered.lower()
    assert "<script " not in rendered.lower()
    assert "&lt;script&gt;alert(&#x27;xss-sec&#x27;)&lt;/script&gt;" in rendered or "&lt;script&gt;alert('xss-sec')&lt;/script&gt;" in rendered


def test_xss_narrative_block_event_handlers_and_tags():
    """Ensure img onerror, svg onload, and iframe vectors are properly neutralized."""
    evil_text = (
        "<img src=x onerror=\"alert('img-xss')\" />"
        "<svg/onload=alert('svg-xss')>"
        "<iframe src=\"javascript:alert('iframe')\"></iframe>"
        "\"><script>alert('breakout')</script>"
        "<a href=\"javascript:alert('link')\">click here</a>"
    )
    state = {
        "metadata": {"number": "M-2026-XSS-EVIL"},
        "blocks": [
            {
                "id": "b_narr2",
                "type": "narrative",
                "section": "OBSERVATIONS",
                "additional_text": evil_text,
            }
        ],
    }
    rendered = render_html(state)
    soup = BeautifulSoup(rendered, "html.parser")

    assert len(soup.find_all("script")) == 0
    assert len(soup.find_all("iframe")) == 0
    assert len(soup.find_all("svg")) == 0

    # Ensure no element has an on* event handler attribute
    for tag in soup.find_all(True):
        for attr in tag.attrs:
            assert not attr.lower().startswith("on"), f"Found event handler {attr} in tag {tag.name}"

    # Dangerous tags must be escaped as HTML entities
    assert "&lt;img" in rendered
    assert "&lt;svg" in rendered
    assert "&lt;iframe" in rendered


def test_xss_table_labels_and_categories():
    """Ensure XSS payloads in table title, grouping_label, category labels/keys, and row cells are escaped."""
    state = {
        "metadata": {"number": "M-2026-XSS-TBL"},
        "blocks": [
            {
                "id": "b_tbl_xss",
                "type": "table",
                "title": "<script>alert('title-xss')</script>",
                "grouping_label": "<b onmouseover=alert(1)>Lot Label</b>",
                "unit": "<script>alert('unit-xss')</script>",
                "categories": [
                    {"key": "cat1", "label": "<img src=x onerror=alert('cat-lbl')>"},
                    {"key": "cat2", "label": "<script>alert('cat-lbl-2')</script>"},
                ],
                "rows": [
                    {
                        "group": "<script>alert('row-group')</script>",
                        "values": {"cat1": 50, "cat2": 50},
                    }
                ],
            }
        ],
    }
    rendered = render_html(state)
    soup = BeautifulSoup(rendered, "html.parser")

    assert len(soup.find_all("script")) == 0
    for tag in soup.find_all(True):
        for attr in tag.attrs:
            assert not attr.lower().startswith("on"), f"Found event handler {attr} on tag {tag.name}"

    # Verify table headers escaped properly
    headers = [th.get_text() for th in soup.find_all("th")]
    assert any("<b onmouseover=alert(1)>" in h or "Lot Label" in h for h in headers)
    assert not soup.find_all("b")  # Should not have parsed <b> tag inside grouping_label


def test_xss_particulars_and_measurements():
    """Ensure particulars labels/values/notes and measurements table fields are escaped."""
    state = {
        "metadata": {"number": "M-2026-XSS-PM"},
        "blocks": [
            {
                "id": "b_part",
                "type": "particulars",
                "section": "<script>alert('part-sec')</script>",
                "rows": [
                    {
                        "label": "<script>alert('part-lbl')</script>",
                        "value": ["<img src=x onerror=alert('part-val')>"],
                        "note": "<svg onload=alert('part-note')>",
                    }
                ],
            },
            {
                "id": "b_meas",
                "type": "measurements",
                "rows": [
                    {
                        "subject": "<script>alert('subj')</script>",
                        "qualifier": "<img src=x onerror=alert('qual')>",
                        "method": "<script>alert('meth')</script>",
                        "min": "<script>alert('min')</script>",
                        "max": "<script>alert('max')</script>",
                        "unit": "<script>alert('unit')</script>",
                    }
                ],
            },
            {
                "id": "b_fixed",
                "type": "fixed_text",
                "content": "<script>alert('fixed-xss')</script>",
            },
        ],
    }
    rendered = render_html(state)
    soup = BeautifulSoup(rendered, "html.parser")

    assert len(soup.find_all("script")) == 0
    for tag in soup.find_all(True):
        for attr in tag.attrs:
            assert not attr.lower().startswith("on"), f"Found event handler {attr} on tag {tag.name}"


def test_xss_live_endpoint_roundtrip(auth_session):
    """Save an adversarial XSS report to the DB and verify preview endpoint renders safely."""
    client, token = auth_session
    payload = {
        "template_id": "perishable-qc-sea",
        "family": "marine_cargo",
        "year": 2026,
        "block_state": {
            "metadata": {"number": "M-2026-ROUNDTRIP-<script>alert(1)</script>"},
            "blocks": [
                {
                    "id": "b_adv",
                    "type": "narrative",
                    "section": "<script>alert('endpoint-sec')</script>",
                    "content": "<img src=x onerror=alert('endpoint-img')>Surveillance check passed.",
                }
            ],
        },
    }
    res = client.post("/api/reports", json=payload)
    assert res.status_code == 201
    report_id = res.json()["id"]

    # Request preview HTML
    preview_res = client.get(f"/api/reports/{report_id}/preview/html")
    assert preview_res.status_code == 200
    assert preview_res.headers["content-type"] == "text/html; charset=utf-8"

    soup = BeautifulSoup(preview_res.text, "html.parser")
    assert len(soup.find_all("script")) == 0
    for tag in soup.find_all(True):
        for attr in tag.attrs:
            assert not attr.lower().startswith("on"), f"Active event handler {attr} found in DOM"


# ===========================================================================
# 2. Endpoint Error Handling (Status Codes & Headers)
# ===========================================================================

@pytest.mark.parametrize(
    "malformed_id",
    [
        "123",
        "not-a-valid-uuid",
        "../../etc/passwd",
        "' OR '1'='1",
        "<script>alert(1)</script>",
        "g" * 36,
        "12345678-1234-1234-1234-12345678901",   # 35 chars
        "12345678-1234-1234-1234-1234567890123", # 37 chars
    ],
)
def test_endpoints_malformed_uuid(auth_session, malformed_id):
    """
    Assert that malformed UUIDs in GET /api/reports/{id} and GET /api/reports/{id}/preview/html
    reject with HTTP 400 Bad Request (or 404 for routing path traversal).
    """
    client, _ = auth_session

    res_report = client.get(f"/api/reports/{malformed_id}")
    res_preview = client.get(f"/api/reports/{malformed_id}/preview/html")

    for res, endpoint in [(res_report, "reports"), (res_preview, "preview")]:
        assert res.status_code in (400, 404), (
            f"Endpoint {endpoint} returned unexpected status {res.status_code} for ID {malformed_id!r}"
        )
        assert res.headers["content-type"].startswith("application/json")
        data = res.json()
        assert "detail" in data
        if res.status_code == 400:
            assert "uuid" in data["detail"].lower() or "invalid" in data["detail"].lower()


def test_endpoints_non_existent_uuid(auth_session):
    """Assert that a valid UUID not present in the database returns 404 Not Found."""
    client, _ = auth_session
    non_existent = str(uuid.uuid4())

    res_report = client.get(f"/api/reports/{non_existent}")
    assert res_report.status_code == 404
    assert res_report.headers["content-type"].startswith("application/json")
    assert "not found" in res_report.json()["detail"].lower()

    res_preview = client.get(f"/api/reports/{non_existent}/preview/html")
    assert res_preview.status_code == 404
    assert res_preview.headers["content-type"].startswith("application/json")
    assert "not found" in res_preview.json()["detail"].lower()


def test_endpoints_unauthorized_missing_token(sample_report_id):
    """Assert that requests without credentials return HTTP 401 Unauthorized with WWW-Authenticate header."""
    unauth_client = TestClient(app)

    res_report = unauth_client.get(f"/api/reports/{sample_report_id}")
    assert res_report.status_code == 401
    assert res_report.headers["content-type"].startswith("application/json")
    assert "www-authenticate" in res_report.headers
    assert res_report.json()["detail"] == "Not authenticated"

    res_preview = unauth_client.get(f"/api/reports/{sample_report_id}/preview/html")
    assert res_preview.status_code == 401
    assert res_preview.headers["content-type"].startswith("application/json")
    assert "www-authenticate" in res_preview.headers
    assert res_preview.json()["detail"] == "Not authenticated"


def test_endpoints_unauthorized_invalid_or_expired_token(sample_report_id):
    """Assert that forged, invalid, or expired tokens return HTTP 401 Unauthorized."""
    unauth_client = TestClient(app)

    # 1. Non-existent / random token
    res1 = unauth_client.get(
        f"/api/reports/{sample_report_id}",
        headers={"Authorization": "Bearer non_existent_token_99999"},
    )
    assert res1.status_code == 401
    assert res1.json()["detail"] == "Session expired or invalid"

    res2 = unauth_client.get(
        f"/api/reports/{sample_report_id}/preview/html",
        headers={"Authorization": "Bearer non_existent_token_99999"},
    )
    assert res2.status_code == 401
    assert res2.json()["detail"] == "Session expired or invalid"

    # 2. Malformed Authorization headers
    for bad_header in ["Bearer", "Basic dXNlcjpwYXNz", "Token xyz"]:
        r = unauth_client.get(
            f"/api/reports/{sample_report_id}",
            headers={"Authorization": bad_header},
        )
        assert r.status_code == 401


@pytest.mark.asyncio
async def test_endpoints_session_expired_in_redis(sample_report_id):
    """Empirically test session expiration: token exists but TTL expires in Redis."""
    unauth_client = TestClient(app)
    r = await get_redis_client()

    short_lived_token = f"adv_test_exp_{uuid.uuid4().hex}"
    session_data = {
        "token": short_lived_token,
        "user_id": str(uuid.uuid4()),
        "email": "temp@example.com",
        "full_name": "Temporary Surveyor",
        "role": "SURVEYOR",
        "created_at": "2026-09-05T00:00:00Z",
    }
    # Set with 1-second TTL
    await r.set(f"session:{short_lived_token}", json.dumps(session_data), ex=1)

    # Immediately verify it works
    r_valid = unauth_client.get(
        f"/api/reports/{sample_report_id}?auth_token={short_lived_token}"
    )
    assert r_valid.status_code == 200

    # Wait for TTL to expire
    await asyncio.sleep(1.2)

    # Now verify it is rejected with 401
    r_expired = unauth_client.get(
        f"/api/reports/{sample_report_id}?auth_token={short_lived_token}"
    )
    assert r_expired.status_code == 401
    assert r_expired.json()["detail"] == "Session expired or invalid"


def test_query_parameter_token_support(auth_session, sample_report_id):
    """
    Empirically test query parameter token support:
    - ?auth_token={token} succeeds with 200 for both GET /api/reports/{id} and preview/html
    - Response headers match specifications: preview has text/html; charset=utf-8
    - ?token={token} fails with 401 (verifying that auth_token is the supported query parameter name)
    """
    _, valid_token = auth_session
    raw_client = TestClient(app)

    # 1. Preview endpoint via ?auth_token=
    res_preview = raw_client.get(
        f"/api/reports/{sample_report_id}/preview/html?auth_token={valid_token}"
    )
    assert res_preview.status_code == 200
    assert res_preview.headers["content-type"] == "text/html; charset=utf-8"
    assert "<!DOCTYPE html>" in res_preview.text
    assert "a4-page" in res_preview.text

    # 2. Report details endpoint via ?auth_token=
    res_report = raw_client.get(
        f"/api/reports/{sample_report_id}?auth_token={valid_token}"
    )
    assert res_report.status_code == 200
    assert res_report.headers["content-type"].startswith("application/json")
    assert res_report.json()["id"] == sample_report_id

    # 3. Query param with expired/invalid token
    res_invalid = raw_client.get(
        f"/api/reports/{sample_report_id}/preview/html?auth_token=forged_token"
    )
    assert res_invalid.status_code == 401

    # 4. Probe ?token= parameter support
    res_tok_param = raw_client.get(
        f"/api/reports/{sample_report_id}/preview/html?token={valid_token}"
    )
    assert res_tok_param.status_code == 401, (
        "Expected 401 because app.core.auth currently only checks ?auth_token"
    )


# ===========================================================================
# 3. Adversarial Probing: LFI & Resilience Edge Cases
# ===========================================================================

def test_lfi_asset_path_exposure_vulnerability(auth_session):
    """
    Adversarial finding test:
    Demonstrates that photo_plate blocks referencing local paths in assets
    read and embed arbitrary files if unconstrained.
    """
    client, token = auth_session
    # Target /etc/hosts which is universally readable on Linux
    payload = {
        "template_id": "perishable-qc-sea",
        "family": "marine_cargo",
        "year": 2026,
        "block_state": {
            "metadata": {"number": "M-2026-LFI-PROBE"},
            "assets": {
                "probe_asset": {
                    "original_path": "/etc/hosts",
                }
            },
            "blocks": [
                {
                    "id": "b_photo",
                    "type": "photo_plate",
                    "label": "Evidence Plate",
                    "groups": [
                        {
                            "id": "g1",
                            "observation": "System file leak test",
                            "asset_ids": ["probe_asset"],
                        }
                    ],
                }
            ],
        },
    }
    res = client.post("/api/reports", json=payload)
    assert res.status_code == 201
    report_id = res.json()["id"]

    preview_res = client.get(f"/api/reports/{report_id}/preview/html")
    assert preview_res.status_code == 200

    html_body = preview_res.text
    has_b64_embed = "data:image/jpeg;base64," in html_body
    if has_b64_embed:
        start = html_body.find("data:image/jpeg;base64,") + len("data:image/jpeg;base64,")
        end = html_body.find('"', start)
        raw_b64 = html_body[start:end]
        decoded = base64.b64decode(raw_b64).decode("utf-8", errors="replace")
        assert "localhost" in decoded, "Expected /etc/hosts content to be embedded via LFI"


def test_unicode_and_special_character_rendering():
    """Verify that multi-byte UTF-8, Arabic RTL, and Emoji characters render cleanly without 500 error."""
    state = {
        "metadata": {"number": "M-2026-UNICODE-🚢"},
        "blocks": [
            {
                "id": "b1",
                "type": "narrative",
                "section": "حالة البضائع 📦",
                "content": "تم فحص الشحنة في ميناء الإسكندرية. 货物状况良好。Все в порядке! 🚢⚓",
            }
        ],
    }
    rendered = render_html(state)
    assert "حالة البضائع 📦" in rendered
    assert "货物状况良好" in rendered
    assert "Все в порядке!" in rendered
    assert "M-2026-UNICODE-🚢" in rendered
