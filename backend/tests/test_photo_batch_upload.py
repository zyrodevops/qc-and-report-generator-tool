"""
Test batch photo upload API endpoint and bit-exact preservation.
"""

import hashlib
import io
import pytest
from fastapi.testclient import TestClient

from app.main import app
from tests.e2e.helpers.synthetic_data import create_synthetic_image_with_exif


def test_batch_photo_upload_endpoint():
    client = TestClient(app)

    # 0. Login
    login_res = client.post(
        "/api/auth/login",
        json={"email": "surveyor@example.com", "password": "Password123!"}
    )
    assert login_res.status_code == 200
    token = login_res.json()["token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 1. Create a draft report
    create_payload = {
        "template_id": "perishable_qc_sea",
        "family": "QC_REPORT",
        "year": 2026,
        "block_state": {
            "metadata": {
                "number": "ALLOCATED_BY_SERVER",
                "family": "QC_REPORT",
                "docx_template": "mca-qc-v1.docx"
            },
            "blocks": [],
            "assets": {},
        }
    }
    res_create = client.post(
        "/api/reports",
        json=create_payload,
        headers=headers,
    )
    assert res_create.status_code == 201
    rep_id = res_create.json()["id"]

    # 2. Create 3 synthetic photos with EXIF
    photo_1 = create_synthetic_image_with_exif()
    photo_2 = create_synthetic_image_with_exif()
    photo_3 = create_synthetic_image_with_exif()

    hash_1 = hashlib.sha256(photo_1).hexdigest()
    hash_2 = hashlib.sha256(photo_2).hexdigest()
    hash_3 = hashlib.sha256(photo_3).hexdigest()

    # 3. Post as batch
    files = [
        ("files", ("photo1.jpg", photo_1, "image/jpeg")),
        ("files", ("photo2.jpg", photo_2, "image/jpeg")),
        ("files", ("photo3.jpg", photo_3, "image/jpeg")),
    ]
    data = {
        "series_id": "survey",
        "provenance": "own_survey",
    }

    res_batch = client.post(
        f"/api/reports/{rep_id}/assets/photos/batch",
        files=files,
        data=data,
        headers=headers,
    )

    assert res_batch.status_code == 201
    batch_json = res_batch.json()
    assert batch_json["count"] == 3
    assets = batch_json["assets"]
    assert len(assets) == 3

    # 4. Verify each asset preserves its bit-exact sha-256 and has valid URLs
    expected_hashes = [hash_1, hash_2, hash_3]
    for i, asset in enumerate(assets):
        assert asset["sha256"] == expected_hashes[i]
        assert asset["exif_integrity"] == "INTACT"
        assert f"/api/reports/{rep_id}/assets/{asset['id']}/image" in asset["url"]

        # Verify image serving
        res_img = client.get(asset["url"])
        assert res_img.status_code == 200
        assert res_img.headers["content-type"] == "image/jpeg"

    # 5. Verify report block_state was updated with all 3 assets
    res_rep = client.get(f"/api/reports/{rep_id}", headers=headers)
    assert res_rep.status_code == 200
    state = res_rep.json()["block_state"]
    assert "assets" in state
    for asset in assets:
        assert asset["id"] in state["assets"]

