"""
Tests for Tally Sheet OCR Ingestion & Verification Pipeline.
Master Spec §10.4, CRITICAL-RULES §5, §7.
"""

import io
import pytest
from decimal import Decimal
from PIL import Image, ImageDraw
from httpx import AsyncClient, ASGITransport

from app.main import app
from app.ingest.tally_ocr import (
    preprocess_tally_image,
    parse_iso_date,
    parse_numeric_range,
    parse_tally_sheet_text,
    parse_tally_image,
)


def test_parse_iso_date():
    assert parse_iso_date("01/09/2026") == "2026-09-01"
    assert parse_iso_date("22-08-2026") == "2026-08-22"
    assert parse_iso_date("26.05.2026") == "2026-05-26"
    assert parse_iso_date("5/3/26") == "2026-03-05"
    assert parse_iso_date("invalid") is None


def test_parse_numeric_range():
    assert parse_numeric_range("4.85") == (Decimal("4.85"), Decimal("4.85"))
    assert parse_numeric_range("3.3 to 4.5") == (Decimal("3.3"), Decimal("4.5"))
    assert parse_numeric_range("0.8 - 1.4") == (Decimal("0.8"), Decimal("1.4"))
    assert parse_numeric_range("-0.1 to 0.5") == (Decimal("-0.1"), Decimal("0.5"))
    assert parse_numeric_range("None") == (None, None)


def test_parse_tally_sheet_text():
    sample_ocr_text = """
    MARINE CARGO AGENCIES - SURVEY TALLY SHEET
    PARTY NAME: Reliance Retail Ltd
    SURVEY DATE: 01/09/2026
    DESTUFF DATE: 30/08/2026
    CONTAINER NO: TTNU8601264
    ROOM NO: 05
    ROOM TEMPERATURE: 4.85
    PULP TEMPERATURE: 3.3 to 4.5
    BRIX: 9.5 to 11.1
    PRESSURE: 16.88 to 17.59

    COUNT SOUND SOFT RUSSET ROTTEN
    Count 50 210 15 45 10
    Count 55 230 18 36 10
    Count 60 190 22 40 8
    Count 70 170 20 30 6
    """
    res = parse_tally_sheet_text(sample_ocr_text)
    headers = res["headers"]

    assert headers["container_number"] == "TTNU8601264"
    assert headers["party_name"] == "Reliance Retail Ltd"
    assert headers["survey_date"] == "2026-09-01"
    assert headers["destuff_date"] == "2026-08-30"
    assert headers["room_no"] == "05"
    assert headers["room_temp"] == 4.85
    assert headers["pulp_temp_min"] == 3.3
    assert headers["pulp_temp_max"] == 4.5
    assert headers["brix_min"] == 9.5
    assert headers["brix_max"] == 11.1
    assert headers["pressure_min"] == 16.88
    assert headers["pressure_max"] == 17.59

    table = res["table"]
    assert len(table["rows"]) == 4
    assert table["rows"][0]["group"] == "Count 50"
    assert table["rows"][0]["values"]["sound"] == 210
    assert table["rows"][0]["values"]["soft"] == 15
    assert table["rows"][0]["values"]["russet"] == 45
    assert table["rows"][0]["values"]["rotten"] == 10
    assert res["provenance"] == "ocr_verified"


def test_tally_image_preprocessing():
    # Create synthetic test image
    img = Image.new("RGB", (400, 600), color=(255, 255, 255))
    draw = ImageDraw.Draw(img)
    draw.text((20, 20), "PARTY NAME: Gajumal", fill=(0, 0, 0))
    draw.text((20, 50), "CONTAINER NO: EMCU5986270", fill=(0, 0, 0))
    draw.text((20, 80), "SURVEY DATE: 22/08/2026", fill=(0, 0, 0))
    draw.text((20, 110), "PULP TEMPERATURE: 0.8 to 1.4", fill=(0, 0, 0))

    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    img_bytes = buf.getvalue()

    display_img, ocr_img = preprocess_tally_image(img_bytes)
    assert display_img.size[0] <= 1200
    assert ocr_img.mode in ["RGB", "L"]

    result = parse_tally_image(img_bytes, filename="test_tally.jpg")
    assert "headers" in result
    assert "table" in result
    assert "image_preview" in result
    assert result["image_preview"].startswith("data:image/jpeg;base64,")
    assert result["provenance"] == "ocr_verified"


@pytest.mark.asyncio
async def test_api_import_tally_ocr_and_apply():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        # 0. Log in to get auth token
        login_res = await ac.post(
            "/api/auth/login",
            json={"email": "surveyor@example.com", "password": "Password123!"},
        )
        assert login_res.status_code == 200, login_res.text
        token = login_res.json()["token"]
        auth_hdr = {"Authorization": f"Bearer {token}"}

        # 1. Create a draft report
        create_res = await ac.post(
            "/api/reports",
            json={
                "family": "QC_REPORT",
                "commodity": "mandarin",
                "template_id": "tpl_qc_mandarin_v1",
            },
            headers=auth_hdr,
        )
        assert create_res.status_code == 201, create_res.text
        report_id = create_res.json()["id"]

        # 2. Upload synthetic tally sheet image
        img = Image.new("RGB", (200, 200), color="white")
        buf = io.BytesIO()
        img.save(buf, format="JPEG")
        img_bytes = buf.getvalue()

        upload_res = await ac.post(
            f"/api/reports/{report_id}/import/tally-ocr",
            files={"file": ("test_tally.jpg", img_bytes, "image/jpeg")},
            headers=auth_hdr,
        )
        assert upload_res.status_code == 200, upload_res.text
        ocr_data = upload_res.json()
        assert "headers" in ocr_data
        assert "table" in ocr_data

        # 3. Apply confirmed OCR data to report
        apply_payload = {
            "headers": {
                "container_number": "TTNU8601264",
                "party_name": "Reliance Retail Ltd",
                "survey_date": "2026-09-01",
                "room_no": "05",
                "room_temp": 4.85,
                "pulp_temp_min": 3.3,
                "pulp_temp_max": 4.5,
                "brix_min": 9.5,
                "brix_max": 11.1,
            },
            "table": {
                "categories": [
                    {"key": "sound", "label": "Sound"},
                    {"key": "soft", "label": "Soft"},
                    {"key": "russet", "label": "Russet"},
                    {"key": "rotten", "label": "Rotten"},
                ],
                "rows": [
                    {"group": "Count 50", "values": {"sound": 210, "soft": 15, "russet": 45, "rotten": 10}},
                    {"group": "Count 55", "values": {"sound": 230, "soft": 18, "russet": 36, "rotten": 10}},
                ],
            },
        }

        apply_res = await ac.post(
            f"/api/reports/{report_id}/import/tally-ocr/apply",
            json=apply_payload,
            headers=auth_hdr,
        )
        assert apply_res.status_code == 200, apply_res.text
        updated_state = apply_res.json()["block_state"]

        # Check that table rows were updated and tagged ocr_verified
        table_block = next(b for b in updated_state["blocks"] if b["type"] == "table")
        assert len(table_block["rows"]) == 2
        assert table_block["rows"][0]["group"] == "Count 50"
        assert table_block["rows"][0]["provenance"] == "ocr_verified"
        assert table_block["rows"][0]["values"]["sound"] == "210"

        # Check measurements block
        measurements_block = next((b for b in updated_state["blocks"] if b["type"] == "measurements"), None)
        if measurements_block:
            pulp_row = next((r for r in measurements_block["rows"] if "pulp" in r.get("subject", "").lower()), None)
            if pulp_row:
                assert pulp_row["min"] == "3.3"
                assert pulp_row["max"] == "4.5"
                assert pulp_row["provenance"] == "ocr_verified"


def test_extract_clean_room_no():
    from app.ingest.tally_ocr import extract_clean_room_no

    # Reject literal label words
    assert extract_clean_room_no(["ROOM NO: ROOM", "ROOM TEMPERATURE: 4.5"], "ROOM NO: ROOM\nROOM TEMPERATURE: 4.5") is None
    assert extract_clean_room_no(["ROOM NO: TEMPERATURE"], "ROOM NO: TEMPERATURE") is None
    assert extract_clean_room_no(["TEMP: 4.5"], "TEMP: 4.5") is None

    # Valid cold room numbers
    assert extract_clean_room_no(["ROOM NO: 05"], "ROOM NO: 05") == "05"
    assert extract_clean_room_no(["ROOM NO: 04"], "ROOM NO: 04") == "04"
    assert extract_clean_room_no(["ROOM NO: 2"], "ROOM NO: 2") == "2"
    assert extract_clean_room_no(["ROOM NO: C5-10"], "ROOM NO: C5-10") == "C5-10"
    assert extract_clean_room_no(["CS-11 & C5-20"], "ROOM: CS-11 & C5-20") == "C5-11 & C5-20"


def test_knowledge_base_catalog():
    from app.ingest.tally_knowledge_base import get_known_tally_match, KNOWN_TALLY_CATALOG

    assert len(KNOWN_TALLY_CATALOG) >= 4
    m_cntr = get_known_tally_match(container_number="EMCU5986270")
    assert m_cntr is not None
    assert m_cntr["party_name"] == "Gajumal"
    assert m_cntr["source_doc"] == "16 Boxes.xlsx"

    m_file = get_known_tally_match(filename="IMG-20260903-WA0064.jpg")
    assert m_file is not None
    assert m_file["container_number"] == "TTNU8601264"
    assert m_file["party_name"] == "Reliance Retail Ltd"


@pytest.mark.asyncio
async def test_api_tally_samples_and_sample_ocr():
    from pathlib import Path
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        login_res = await ac.post(
            "/api/auth/login",
            json={"email": "surveyor@example.com", "password": "Password123!"},
        )
        assert login_res.status_code == 200
        auth_hdr = {"Authorization": f"Bearer {login_res.json()['token']}"}

        create_res = await ac.post(
            "/api/reports",
            json={"family": "QC_REPORT", "commodity": "mandarin", "template_id": "tpl_qc_mandarin_v1"},
            headers=auth_hdr,
        )
        assert create_res.status_code == 201
        report_id = create_res.json()["id"]

        # Test GET /api/reports/{id}/import/tally-samples
        samples_res = await ac.get(f"/api/reports/{report_id}/import/tally-samples", headers=auth_hdr)
        assert samples_res.status_code == 200
        samples = samples_res.json()
        assert isinstance(samples, list)
        assert len(samples) >= 4

        # Test POST /api/reports/{id}/import/tally-ocr with sample_id="WA0064"
        sample_ocr_res = await ac.post(
            f"/api/reports/{report_id}/import/tally-ocr",
            data={"sample_id": "WA0064"},
            headers=auth_hdr,
        )
        assert sample_ocr_res.status_code == 200, sample_ocr_res.text
        res_data = sample_ocr_res.json()
        assert res_data["headers"]["container_number"] == "TTNU8601264"
        assert res_data["headers"]["party_name"] == "Reliance Retail Ltd"
        assert res_data["headers"]["room_no"] == "05"
        assert res_data.get("knowledge_base_match") is not None
        assert res_data["knowledge_base_match"]["id"] == "WA0064"


def test_easyocr_engine_loaded():
    from app.ingest.tally_ocr import HAS_EASYOCR, get_easyocr_reader
    assert HAS_EASYOCR is True
    reader = get_easyocr_reader()
    assert reader is not None


def test_clean_container_no_variations():
    from app.ingest.tally_ocr import clean_container_no
    assert clean_container_no("HLBU 94.45331") == "HLBU9445331"
    assert clean_container_no("EMCU 598627O") == "EMCU5986270"
    assert clean_container_no("TTNU8601264") == "TTNU8601264"
    assert clean_container_no("TCNU-1234567") == "TCNU1234567"
    assert clean_container_no("invalid") is None


def test_clean_ocr_date_variations():
    from app.ingest.tally_ocr import clean_ocr_date
    assert clean_ocr_date("SURVEY DATE:26 05/2026") == "2026-05-26"
    assert clean_ocr_date("DESTUFF DATE: 23 1o5/o26") == "2026-05-23"
    assert clean_ocr_date("01/09/2026") == "2026-09-01"
    assert clean_ocr_date("22-08-2026") == "2026-08-22"
    assert clean_ocr_date("5/3/26") == "2026-03-05"


def test_extract_clean_room_no_advanced():
    from app.ingest.tally_ocr import extract_clean_room_no
    assert extract_clean_room_no(["ROOM NO : cS-lo"], "ROOM NO : cS-lo") == "C5-10"
    assert extract_clean_room_no(["ROOM: C5-10"], "ROOM: C5-10") == "C5-10"
    assert extract_clean_room_no(["ROOM NO: 05"], "ROOM NO: 05") == "05"
    assert extract_clean_room_no(["ROOM NO: ROOM"], "ROOM NO: ROOM") is None
    assert extract_clean_room_no(["ROOM NO: TEMPERATURE"], "ROOM NO: TEMPERATURE") is None

