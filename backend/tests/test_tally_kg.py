"""
Weighed fruit: grapes, blueberries and cherries are tallied in kg a box.

Every step used to assume whole counts. A weight of 0.820 was either refused
as not-a-number or read as 820 pieces, and the server's recheck ran int() over
it. These tests hold the three-place weights through the whole path.
"""

from decimal import Decimal

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.ingest.tally.categories import build_categories
from app.ingest.tally.normalization import NumericNormalizer
from app.ingest.tally.spreadsheet_grid import read_spreadsheet_as_grid
from app.ingest.tally.validation import ValidationEngine

CANONICAL_TEMPLATE = "perishable_qc_sea"


def test_weights_keep_three_places():
    n = NumericNormalizer()
    assert n.normalize_weight("0.820")[0] == Decimal("0.820")
    assert n.normalize_weight("0,82")[0] == Decimal("0.820")  # comma for the dot
    assert n.normalize_weight("O.52O")[0] == Decimal("0.520")  # O read for 0
    assert n.normalize_weight("nil")[0] == Decimal("0.000")


def test_weight_without_its_point_is_flagged_not_guessed():
    # "820" in a kg box could be 0.820 or 8.20; the surveyor decides.
    val, _, ambiguous = NumericNormalizer().normalize_weight("820")
    assert val is None and ambiguous is True


def test_quantity_follows_the_unit():
    n = NumericNormalizer()
    assert n.normalize_quantity("0.820", "kg")[0] == Decimal("0.820")
    assert n.normalize_quantity("120", "pcs")[0] == 120


def test_weights_add_up_exactly():
    # As floats 0.82 + 0.52 + 0.12 is 1.4599999999999997 and would not tie out.
    values = {"sound": Decimal("0.820"), "soft": Decimal("0.520"), "rotten": Decimal("0.120")}
    total, check = ValidationEngine.validate_row_total(values, Decimal("1.460"))
    assert total == Decimal("1.460")
    assert check.status == "PASSED"

    _, bad = ValidationEngine.validate_row_total(values, Decimal("1.500"))
    assert bad.status == "FAILED"


def test_server_recheck_keeps_weights():
    from app.api.assets import _recheck_rows

    rows = _recheck_rows(
        [{"group": "Box 1", "values": {"sound": "0.82", "soft": 0.52, "rotten": "0.120"}, "stated_total": "1.46"}],
        "kg",
    )
    assert rows[0]["values"] == {"sound": Decimal("0.820"), "soft": Decimal("0.520"), "rotten": Decimal("0.120")}
    assert rows[0]["computed_total"] == Decimal("1.460")
    assert rows[0]["check"]["status"] == "OK"


def test_server_recheck_does_not_cut_a_count_down():
    from app.api.assets import _recheck_rows

    rows = _recheck_rows([{"group": "A", "values": {"sound": "2.5", "rotten": 3}, "stated_total": 3}], "pcs")
    # 2.5 is not a count; it is left out, not turned into 2.
    assert "sound" not in rows[0]["values"]


def test_kg_spreadsheet_rows_are_not_dropped_as_percentages():
    csv = (
        "Box,Sound,Soft,Rotten,Total\n"
        "1,0.82,0.52,0.12,1.46\n"
        "2,0.9,0.3,0.1,1.3\n"
    ).encode()
    grid = read_spreadsheet_as_grid(csv, "tally.csv", commodity="GRAPE")
    rows = grid["table"]["rows"]
    assert grid["table"]["unit"] == "kg"
    assert len(rows) == 2
    assert rows[0]["values"]["sound"] == Decimal("0.820")
    assert rows[0]["check"]["status"] == "OK"
    assert rows[1]["stated_total"] == Decimal("1.300")


def test_photo_total_column_is_the_written_total_not_a_defect():
    """
    The reader sometimes hands back the sheet's TOTAL column as one more cell.
    Counted as a column, every grapes box read as twice its weight.
    """
    import io
    from PIL import Image
    from app.ingest.tally.cloud_reader import CloudReadResult, CloudRow
    from app.ingest.tally.pipeline import TallyPipeline

    buf = io.BytesIO()
    Image.new("RGB", (600, 600), "white").save(buf, format="JPEG")
    cloud = CloudReadResult(
        configured=True,
        used=True,
        rows=[
            CloudRow(group="1", values={"sound": 0.82, "soft": 0.52, "rotten": 0.12, "total": 1.46}),
            CloudRow(group="Total", values={"sound": 0.82, "soft": 0.52, "rotten": 0.12, "total": 1.46},
                     is_grand_total=True),
        ],
        discovered_columns=["Total"],
        model="test",
    )
    result = TallyPipeline().build_cloud_result(
        image_bytes=buf.getvalue(), cloud=cloud, categories=build_categories("GRAPE"),
        commodity="GRAPE", filename="sheet.jpg",
    )
    table = result["table"]
    assert "total" not in [c["key"] for c in table["categories"]]
    assert len(table["rows"]) == 1
    row = table["rows"][0]
    assert "total" not in row["values"]
    assert row["stated_total"] == Decimal("1.460")
    assert row["check"]["status"] == "OK"
    assert table["sheet_totals"]["stated_total"] == Decimal("1.460")


@pytest.mark.asyncio
async def test_apply_stores_weights_as_text_with_three_places():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        res = await ac.post("/api/auth/login", json={"password": "surveyor123"})
        hdr = {"Authorization": f"Bearer {res.json()['token']}"}
        created = await ac.post(
            "/api/reports",
            json={"family": "QC_REPORT", "commodity": "GRAPE", "template_id": CANONICAL_TEMPLATE},
            headers=hdr,
        )
        assert created.status_code == 201, created.text
        report_id = created.json()["id"]

        payload = {
            "headers": {},
            "table": {
                "categories": build_categories("GRAPES"),
                "unit": "kg",
                "rows": [
                    {"group": "Box 1", "values": {"sound": 0.82, "soft": 0.52, "rotten": 0.12}, "stated_total": 1.46},
                ],
            },
        }
        res = await ac.post(f"/api/reports/{report_id}/import/tally-ocr/apply", json=payload, headers=hdr)
        assert res.status_code == 200, res.text
        table = next(b for b in res.json()["block_state"]["blocks"] if b["type"] == "table")
        assert table["unit"] == "kg"
        assert table["rows"][0]["values"] == {"sound": "0.820", "soft": "0.520", "rotten": "0.120"}
        assert table["rows"][0]["stated_total"] == "1.460"

        # A weight that does not add up is refused, and the message shows it.
        payload["table"]["rows"][0]["stated_total"] = 1.5
        res = await ac.post(f"/api/reports/{report_id}/import/tally-ocr/apply", json=payload, headers=hdr)
        assert res.status_code == 422
        assert "-0.040" in str(res.json()["detail"]["rows"])

        await ac.delete(f"/api/reports/{report_id}", headers=hdr)
