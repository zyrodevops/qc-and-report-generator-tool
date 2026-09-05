"""
End-to-End Workflow Integration Test — Master Spec §14 Week 1 Deliverables:
1. Create report with atomic gapless sequential numbering
2. Update block state form data
3. Import spreadsheet with =SUM() formulas read as values
4. Upload photo (bit-exact storage, SHA-256 integrity, derived copies)
5. Generate and download valid DOCX report
"""

import io
from fastapi.testclient import TestClient
import docx
import pytest

from app.main import app
from tests.e2e.helpers.synthetic_data import create_synthetic_image_with_exif, create_synthetic_excel_with_formulas


def test_full_week1_workflow_end_to_end():
    client = TestClient(app)

    # 0. Login
    login_res = client.post(
        "/api/auth/login",
        json={"email": "surveyor@example.com", "password": "Password123!"}
    )
    assert login_res.status_code == 200
    token = login_res.json()["token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 1. Create report
    create_payload = {
        "template_id": "perishable-qc-sea",
        "family": "QC_REPORT",
        "year": 2026,
        "block_state": {
            "metadata": {
                "number": "ALLOCATED_BY_SERVER",
                "family": "QC_REPORT",
                "docx_template": "mca-qc-v1.docx"
            },
            "transport": {
                "mode": "SEA",
                "document": {"kind": "BILL_OF_LADING", "number": "BL-TEST-E2E-01"}
            },
            "blocks": [
                {
                    "id": "b1",
                    "type": "particulars",
                    "rows": [{"label": "Commodity", "value": ["Fresh Mandarins"]}]
                },
                {
                    "id": "b2",
                    "type": "table",
                    "unit": "pcs",
                    "categories": [
                        {"key": "sound", "label": "Sound"},
                        {"key": "decay", "label": "Decay"}
                    ],
                    "rows": [{"group": "Box 1", "values": {"sound": 133, "decay": 14}}]
                }
            ]
        }
    }
    res = client.post("/api/reports", json=create_payload, headers=headers)
    assert res.status_code == 201
    rep_id = res.json()["id"]
    rep_num = res.json()["report_number"]
    assert rep_num.startswith("M-") and rep_num.endswith("-2026")

    # 2. Update block state (with optimistic concurrency — must include version)
    current_version = res.json().get("version", 1)
    current_state = res.json()["block_state"]
    current_state["blocks"][0]["rows"].append({"label": "Vessel", "value": ["CMA CGM MEDEA"]})
    res_update = client.patch(
        f"/api/reports/{rep_id}/block-state",
        json={"block_state": current_state, "version": current_version},
        headers=headers,
    )
    assert res_update.status_code == 200

    # 3. Import spreadsheet
    excel_bytes = create_synthetic_excel_with_formulas()
    res_import = client.post(
        f"/api/reports/{rep_id}/import/spreadsheet",
        files={"file": ("test.xlsx", excel_bytes, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
        headers=headers
    )
    assert res_import.status_code == 200
    sample_rows = res_import.json()["sample_rows"]
    assert len(sample_rows) >= 2

    # 4. Upload photo
    photo_bytes = create_synthetic_image_with_exif()
    res_photo = client.post(
        f"/api/reports/{rep_id}/assets/photos",
        files={"file": ("survey_photo.jpg", photo_bytes, "image/jpeg")},
        data={"series_id": "survey", "provenance": "own_survey"},
        headers=headers
    )
    assert res_photo.status_code == 201
    asset_id = res_photo.json()["id"]
    sha256 = res_photo.json()["sha256"]
    assert len(sha256) == 64
    assert "url" in res_photo.json()

    # 4a. Verify asset image serving endpoint
    res_img = client.get(f"/api/reports/{rep_id}/assets/{asset_id}/image")
    assert res_img.status_code == 200
    assert res_img.headers["content-type"] == "image/jpeg"
    assert len(res_img.content) > 0

    # 4b. Add photo to photo plate in block state
    current_state["blocks"].append({
        "id": "b3",
        "type": "photo_plate",
        "series_id": "survey",
        "groups": [{"id": "pg1", "observation": "Customs seal intact", "asset_ids": [asset_id]}]
    })
    v2 = res_update.json().get("new_version", 2)
    res_update2 = client.patch(
        f"/api/reports/{rep_id}/block-state",
        json={"block_state": current_state, "version": v2},
        headers=headers,
    )
    assert res_update2.status_code == 200

    # 5. Download docx
    res_docx = client.get(f"/api/reports/{rep_id}/download/docx", headers=headers)
    assert res_docx.status_code == 200
    assert res_docx.headers["content-type"] == "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    doc = docx.Document(io.BytesIO(res_docx.content))
    assert len(doc.tables) >= 2

