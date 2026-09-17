"""
Tests for tally sheet ingestion and the Verification Workbench.

A large part of this file exists to hold a line that was crossed once: the
pipeline used to fill thin OCR results in from a table of four previous
shipments, matched by container number or by filename, and hand the result back
marked as read from the uploaded image. Several tests below assert that the
fabrication paths are gone and stay gone.
"""

import io
from decimal import Decimal

import pytest
from httpx import ASGITransport, AsyncClient
from PIL import Image, ImageDraw

from app.main import app
from app.ingest.tally.categories import build_categories, is_total_header, match_header_to_category, unit_for
from app.ingest.tally.normalization import NumericNormalizer
from app.ingest.tally.pipeline import available_engines
from app.ingest.tally.validation import ValidationEngine
from app.ingest.tally_ocr import (
    clean_container_no,
    clean_ocr_date,
    extract_clean_room_no,
    parse_iso_date,
    parse_numeric_range,
    parse_tally_image,
    parse_tally_sheet_text,
    preprocess_tally_image,
)

CANONICAL_TEMPLATE = "perishable_qc_sea"


# ---------------------------------------------------------------------------
# Field cleaners
# ---------------------------------------------------------------------------

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


def test_clean_container_no_variations():
    assert clean_container_no("HLBU 94.45331") == "HLBU9445331"
    assert clean_container_no("EMCU 598627O") == "EMCU5986270"
    assert clean_container_no("TTNU8601264") == "TTNU8601264"
    assert clean_container_no("TCNU-1234567") == "TCNU1234567"
    assert clean_container_no("invalid") is None


def test_clean_ocr_date_variations():
    assert clean_ocr_date("SURVEY DATE:26 05/2026") == "2026-05-26"
    assert clean_ocr_date("DESTUFF DATE: 23 1o5/o26") == "2026-05-23"
    assert clean_ocr_date("01/09/2026") == "2026-09-01"
    assert clean_ocr_date("22-08-2026") == "2026-08-22"
    assert clean_ocr_date("5/3/26") == "2026-03-05"


def test_extract_clean_room_no():
    # The label itself must never be returned as the value.
    assert extract_clean_room_no(["ROOM NO: ROOM"], "ROOM NO: ROOM") is None
    assert extract_clean_room_no(["ROOM NO: TEMPERATURE"], "ROOM NO: TEMPERATURE") is None
    assert extract_clean_room_no(["TEMP: 4.5"], "TEMP: 4.5") is None

    assert extract_clean_room_no(["ROOM NO: 05"], "ROOM NO: 05") == "05"
    assert extract_clean_room_no(["ROOM NO: 2"], "ROOM NO: 2") == "2"
    assert extract_clean_room_no(["ROOM NO: C5-10"], "ROOM NO: C5-10") == "C5-10"
    assert extract_clean_room_no(["ROOM NO : cS-lo"], "ROOM NO : cS-lo") == "C5-10"
    assert extract_clean_room_no(["CS-11 & C5-20"], "ROOM: CS-11 & C5-20") == "C5-11 & C5-20"


# ---------------------------------------------------------------------------
# No fabrication
# ---------------------------------------------------------------------------

def test_knowledge_base_module_is_gone():
    """
    The reference table of previous shipments must not come back.

    It matched an uploaded sheet on filename alone, and WhatsApp names photos
    from a rolling counter, so an unrelated sheet could pick up another
    consignment's party, container and defect counts.
    """
    with pytest.raises(ImportError):
        import app.ingest.tally_knowledge_base  # noqa: F401


def test_header_parser_returns_no_table():
    """
    Whole-page text yields headers only.

    Rows used to be built by taking the numbers on a line positionally as
    sound/soft/russet/rotten. Without reading the sheet's own column headers
    that guess puts counts under the wrong defect on any sheet whose columns
    differ, which is most of them.
    """
    text = """
    PARTY NAME: Some Importer Pvt Ltd
    SURVEY DATE: 01/09/2026
    DESTUFF DATE: 30/08/2026
    CONTAINER NO: TTNU8601264
    ROOM NO: 05
    ROOM TEMPERATURE: 4.85
    PULP TEMPERATURE: 3.3 to 4.5
    BRIX: 9.5 to 11.1
    PRESSURE: 16.88 to 17.59
    Count 50 210 15 45 10
    """
    res = parse_tally_sheet_text(text)

    assert "table" not in res
    h = res["headers"]
    assert h["container_number"] == "TTNU8601264"
    assert h["party_name"] == "Some Importer Pvt Ltd"
    assert h["survey_date"] == "2026-09-01"
    assert h["destuff_date"] == "2026-08-30"
    assert h["room_no"] == "05"
    assert h["room_temp"] == 4.85
    assert (h["pulp_temp_min"], h["pulp_temp_max"]) == (3.3, 4.5)
    assert (h["brix_min"], h["brix_max"]) == (9.5, 11.1)


def test_party_name_is_never_resolved_from_a_known_customer_list():
    """A substring must not be expanded into a full company name."""
    res = parse_tally_sheet_text("PARTY NAME: Relia Trading\nCONTAINER NO: TTNU8601264")
    assert res["headers"]["party_name"] == "Relia Trading"


def test_blank_sheet_yields_no_rows():
    """An image with no grid produces an empty table, not a placeholder one."""
    img = Image.new("RGB", (900, 1200), color="white")
    buf = io.BytesIO()
    img.save(buf, format="JPEG")

    result = parse_tally_image(buf.getvalue(), filename="IMG-20260917-WA0065.jpg", commodity="APPLE")

    assert result["table"]["rows"] == []
    assert result["headers"]["container_number"] is None
    assert result["headers"]["party_name"] is None
    assert result["extraction_status"] in ("NO_GRID", "PARTIAL", "NO_ENGINE")
    # Read by a machine at best; never presented as checked by a person.
    assert result["provenance"] == "ocr_extracted"


# ---------------------------------------------------------------------------
# Fruit-driven columns
# ---------------------------------------------------------------------------

def test_columns_come_from_the_commodity():
    apple = [c["label"] for c in build_categories("APPLE")]
    kiwi = [c["label"] for c in build_categories("KIWI")]

    assert apple[0] == "Sound" and kiwi[0] == "Sound"
    assert "Lenticels" in apple and "Lenticels" not in kiwi
    assert "Butterfly" in kiwi and "Butterfly" not in apple


def test_unit_follows_the_commodity():
    assert unit_for("BLUEBERRY") == "kg"
    assert unit_for("APPLE") == "pcs"
    assert unit_for(None) == "pcs"


def test_unknown_commodity_does_not_invent_columns():
    """Better one honest column than a set of defects this fruit is not graded on."""
    assert [c["key"] for c in build_categories(None)] == ["sound"]
    assert [c["key"] for c in build_categories("NOT_A_FRUIT")] == ["sound"]


def test_header_matching_tolerates_corpus_spellings():
    cats = build_categories("APPLE")
    assert match_header_to_category("Mechaniical Injury", cats) == "mechanical_injury"
    assert match_header_to_category("Mechanical", cats) == "mechanical_injury"
    assert match_header_to_category("Sound", cats) == "sound"
    assert match_header_to_category("Zz", cats) is None

    assert is_total_header("TOTAL") and is_total_header("Sum")
    assert not is_total_header("Sound")


# ---------------------------------------------------------------------------
# Reading cells
# ---------------------------------------------------------------------------

def test_unreadable_cell_is_not_silently_zero():
    """
    A cell OCR returned nothing for is unknown, not zero.

    Zero is a real count that shifts every percentage in the finished report,
    and nobody reviewing the grid would see that it had been assumed.
    """
    val, _, ambiguous = NumericNormalizer.normalize_integer("")
    assert val is None and ambiguous is True

    # A mark the surveyor actually wrote is unambiguous.
    assert NumericNormalizer.normalize_integer("-")[0] == 0
    assert NumericNormalizer.normalize_integer("nil")[0] == 0


def test_letters_are_not_mangled_into_numbers():
    """'ABC' used to normalise to 8, because B maps to 8 and the rest was stripped."""
    assert NumericNormalizer.normalize_integer("ABC")[0] is None
    # A genuine letter-for-digit misread is still repaired.
    assert NumericNormalizer.normalize_integer("l2")[0] == 12
    assert NumericNormalizer.normalize_integer("1O")[0] == 10


def test_run_together_cells_are_rejected():
    """Five digits in one cell of a per-box count is two cells read as one."""
    assert NumericNormalizer.normalize_integer("123456")[0] is None
    assert NumericNormalizer.normalize_integer("9999")[0] == 9999


# ---------------------------------------------------------------------------
# The row check
# ---------------------------------------------------------------------------

def test_row_check_has_three_outcomes():
    values = {"sound": 180, "rotten": 5, "bruised": 15}

    total, ok = ValidationEngine.validate_row_total(values, 200)
    assert (total, ok.status) == (200, "PASSED")

    total, bad = ValidationEngine.validate_row_total(values, 210)
    assert (total, bad.status) == (200, "FAILED")
    assert "210" in bad.message

    # No written total means nothing to check against — not a pass.
    total, none = ValidationEngine.validate_row_total(values, None)
    assert (total, none.status) == (200, "SKIPPED")


def test_row_check_never_edits_values_to_make_them_agree():
    values = {"sound": 100, "rotten": 1}
    before = dict(values)
    ValidationEngine.validate_row_total(values, 999)
    assert values == before


def test_server_recomputes_totals_it_is_sent():
    """A total posted by a browser is discarded and derived again from the cells."""
    from app.api.assets import _recheck_rows

    rows = _recheck_rows([
        {"group": "A", "values": {"sound": 1, "rotten": 1}, "stated_total": 2, "computed_total": 999},
    ])
    assert rows[0]["computed_total"] == 2
    assert rows[0]["check"]["status"] == "OK"


# ---------------------------------------------------------------------------
# Engine reporting
# ---------------------------------------------------------------------------

def test_available_engines_reports_what_is_installed():
    """
    OCR engines are optional, so this reports rather than asserts.

    The workbench needs the list to tell the surveyor that nothing was read
    because no reader is installed, instead of showing an empty grid and
    leaving him to conclude his sheet was unreadable.
    """
    engines = available_engines()
    assert isinstance(engines, list)
    assert all(isinstance(e, str) for e in engines)


def test_image_preprocessing():
    img = Image.new("RGB", (400, 600), color=(255, 255, 255))
    draw = ImageDraw.Draw(img)
    draw.text((20, 20), "CONTAINER NO: TTNU8601264", fill=(0, 0, 0))

    buf = io.BytesIO()
    img.save(buf, format="JPEG")

    display_img, ocr_img = preprocess_tally_image(buf.getvalue())
    assert display_img.size[0] <= 1200
    assert ocr_img.mode == "RGB"


# ---------------------------------------------------------------------------
# API
# ---------------------------------------------------------------------------

async def _login(ac: AsyncClient) -> dict:
    res = await ac.post("/api/auth/login", json={"password": "surveyor123"})
    assert res.status_code == 200, res.text
    return {"Authorization": f"Bearer {res.json()['token']}"}


@pytest.mark.asyncio
async def test_capabilities_endpoint_reports_columns_and_engines():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        hdr = await _login(ac)
        created = await ac.post(
            "/api/reports",
            json={"family": "QC_REPORT", "commodity": "APPLE", "template_id": CANONICAL_TEMPLATE},
            headers=hdr,
        )
        assert created.status_code == 201, created.text
        report_id = created.json()["id"]

        res = await ac.get(
            f"/api/reports/{report_id}/import/tally/capabilities?commodity=APPLE", headers=hdr
        )
        assert res.status_code == 200, res.text
        caps = res.json()

        assert caps["unit"] == "pcs"
        labels = [c["label"] for c in caps["categories"]]
        assert labels[0] == "Sound" and "Lenticels" in labels
        assert isinstance(caps["ocr_engines"], list)
        assert caps["ocr_available"] == bool(caps["ocr_engines"])

        # The hosted reader is the main path when a key is configured, and the
        # local engines run otherwise. Asserted as a relationship rather than a
        # fixed value, because whether a key is present depends on the machine
        # this runs on and neither state is a failure.
        assert isinstance(caps["cloud_reader"], bool)
        expected = "cloud" if caps["cloud_reader"] else ("local" if caps["ocr_engines"] else "none")
        assert caps["reader"] == expected


@pytest.mark.asyncio
async def test_apply_refuses_rows_that_do_not_add_up():
    """
    A row whose cells disagree with its written total is rejected.

    One of the two numbers is wrong, and the report goes out under an IRDAI
    licence. Storing it and hoping someone spots it later is not an option.
    """
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        hdr = await _login(ac)
        created = await ac.post(
            "/api/reports",
            json={"family": "QC_REPORT", "commodity": "APPLE", "template_id": CANONICAL_TEMPLATE},
            headers=hdr,
        )
        assert created.status_code == 201, created.text
        report_id = created.json()["id"]

        payload = {
            "headers": {},
            "table": {
                "categories": build_categories("APPLE"),
                "unit": "pcs",
                "rows": [
                    {"group": "Count 120", "values": {"sound": 180, "rotten": 5}, "stated_total": 999},
                ],
            },
        }
        res = await ac.post(
            f"/api/reports/{report_id}/import/tally-ocr/apply", json=payload, headers=hdr
        )
        assert res.status_code == 422, res.text
        assert "Count 120" in str(res.json()["detail"]["rows"])


@pytest.mark.asyncio
async def test_apply_stores_checked_rows_as_surveyor_verified():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        hdr = await _login(ac)
        created = await ac.post(
            "/api/reports",
            json={"family": "QC_REPORT", "commodity": "APPLE", "template_id": CANONICAL_TEMPLATE},
            headers=hdr,
        )
        assert created.status_code == 201, created.text
        report_id = created.json()["id"]

        payload = {
            "headers": {"container_number": "TTNU8601264", "pulp_temp_min": 3.3, "pulp_temp_max": 4.5},
            "table": {
                "categories": build_categories("APPLE"),
                "unit": "pcs",
                "rows": [
                    {"group": "Count 120", "values": {"sound": 180, "rotten": 5}, "stated_total": 185},
                    {"group": "Count 150", "values": {"sound": 190, "rotten": 4}, "stated_total": None},
                ],
            },
        }
        res = await ac.post(
            f"/api/reports/{report_id}/import/tally-ocr/apply", json=payload, headers=hdr
        )
        assert res.status_code == 200, res.text

        blocks = res.json()["block_state"]["blocks"]
        table = next(b for b in blocks if b["type"] == "table")
        assert len(table["rows"]) == 2
        assert table["rows"][0]["group"] == "Count 120"
        # Values are stored as strings so the renderer can use Decimal.
        assert table["rows"][0]["values"]["sound"] == "180"
        assert table["rows"][0]["stated_total"] == 185
        assert table["rows"][0]["provenance"] == "surveyor_verified"
