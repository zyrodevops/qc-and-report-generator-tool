"""
A cargo of more than one fruit, and of more than one container.

Each fruit gets its own condition-found table, laid out for that fruit. A
table can carry a Container column; with it on, a tally sheet that names its
container replaces only that container's rows, so the sheets of several
containers gather in one table instead of each wiping out the last.
"""

import docx
import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.ingest.tally.categories import build_categories
from app.render.docx.engine import render_table
from app.render.html.engine import render_table_html
from app.render.table_columns import shows_container
from app.seeds.defaults import UnknownCommodity, fruit_table_block

C1, C2 = "TSTU1234565", "TSTU7654326"


def _table(show_container=True):
    return {
        "id": "t", "type": "table", "title": "CONDITION FOUND", "unit": "pcs",
        "grouping_label": "Count",
        "categories": [{"key": "sound", "label": "Sound"}, {"key": "rot", "label": "Rot"}],
        "rows": [
            {"group": "100", "container": C1, "values": {"sound": "90", "rot": "10"}},
            {"group": "113", "container": C2, "values": {"sound": "80", "rot": "20"}},
        ],
        "show_container": show_container,
        "show_chart": False,
    }


def test_each_fruit_gets_its_own_layout():
    grapes = fruit_table_block("GRAPES", "b_x")
    assert grapes["commodity"] == "GRAPE" and grapes["unit"] == "kg" and grapes["rows"] == []
    apples = fruit_table_block("apple", "b_y")
    assert apples["unit"] == "pcs"
    assert [c["key"] for c in grapes["categories"]] != [c["key"] for c in apples["categories"]]
    with pytest.raises(UnknownCommodity):
        fruit_table_block("DRAGONFRUIT", "b_z")


def test_container_column_only_when_ticked_and_filled():
    assert shows_container(_table())
    assert not shows_container(_table(show_container=False))
    empty = _table()
    for r in empty["rows"]:
        r.pop("container")
    assert not shows_container(empty)


def test_container_column_prints_in_html_and_word():
    computed = {"row_totals": [100, 100], "column_totals": {"sound": 170, "rot": 30},
                "grand_total": 200, "column_percentages": {"sound": "85.00", "rot": "15.00"}}

    out = render_table_html(_table(), computed)
    assert "<th>Count</th><th>Container</th><th>Sound</th>" in out
    assert f"<td>100</td><td>{C1}</td><td>90</td>" in out
    assert "<td>Total</td><td></td><td>170</td>" in out
    assert "Container" not in render_table_html(_table(show_container=False), computed)

    d = docx.Document()
    render_table(d, _table(), computed)
    t = d.tables[0]
    assert [c.text for c in t.rows[0].cells] == ["Count", "Container", "Sound", "Rot", "Total (pcs)"]
    assert [c.text for c in t.rows[1].cells][:3] == ["100", C1, "90"]
    assert [c.text for c in t.rows[-2].cells] == ["Total", "", "170", "30", "200"]


def _sheet(container, rows, unit="pcs", cats=None):
    return {
        "headers": {"container_number": container},
        "table": {"categories": cats or build_categories("APPLE"), "unit": unit, "rows": rows},
    }


@pytest.mark.asyncio
async def test_second_fruit_table_and_sheets_per_container():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        res = await ac.post("/api/auth/login", json={"password": "surveyor123"})
        hdr = {"Authorization": f"Bearer {res.json()['token']}"}
        created = await ac.post(
            "/api/reports",
            json={"family": "QC_REPORT", "commodity": "APPLE", "template_id": "perishable_qc_sea"},
            headers=hdr,
        )
        assert created.status_code == 201, created.text
        rid = created.json()["id"]
        try:
            # A table for the second fruit is built for that fruit, not saved.
            res = await ac.get(f"/api/reports/{rid}/tables/new", params={"commodity": "GRAPES"}, headers=hdr)
            assert res.status_code == 200, res.text
            grapes = res.json()["block"]
            assert grapes["id"] == "b_table_grape" and grapes["unit"] == "kg"
            res = await ac.get(f"/api/reports/{rid}/tables/new", params={"commodity": "NOPE"}, headers=hdr)
            assert res.status_code == 400

            # Save it, and tick the Container column on the apple table.
            rep = (await ac.get(f"/api/reports/{rid}", headers=hdr)).json()
            state = rep["block_state"]
            apple = next(b for b in state["blocks"] if b["type"] == "table")
            apple["show_container"] = True
            at = state["blocks"].index(apple)
            state["blocks"].insert(at + 1, grapes)
            res = await ac.patch(f"/api/reports/{rid}/block-state",
                                 json={"block_state": state, "version": rep["version"]}, headers=hdr)
            assert res.status_code == 200, res.text

            url = f"/api/reports/{rid}/import/tally-ocr/apply"
            first = _sheet(C1, [{"group": "100", "values": {"sound": 90, "bruise": 10}, "stated_total": 100}])
            second = _sheet(C2, [{"group": "113", "values": {"sound": 80, "bruise": 20}, "stated_total": 100}])
            assert (await ac.post(url, json={**first, "block_id": apple["id"]}, headers=hdr)).status_code == 200
            res = await ac.post(url, json={**second, "block_id": apple["id"]}, headers=hdr)
            assert res.status_code == 200, res.text
            rows = next(b for b in res.json()["block_state"]["blocks"] if b["id"] == apple["id"])["rows"]
            assert [(r["group"], r["container"]) for r in rows] == [("100", C1), ("113", C2)]

            # The first sheet read again replaces its own rows, in their place.
            again = _sheet(C1, [{"group": "100", "values": {"sound": 95, "bruise": 5}, "stated_total": 100}])
            res = await ac.post(url, json={**again, "block_id": apple["id"]}, headers=hdr)
            blocks = res.json()["block_state"]["blocks"]
            rows = next(b for b in blocks if b["id"] == apple["id"])["rows"]
            assert [(r["container"], r["values"]["sound"]) for r in rows] == [(C1, "95"), (C2, "80")]
            # The grapes table was not touched.
            assert next(b for b in blocks if b["id"] == "b_table_grape")["rows"] == []

            # A kg sheet cannot go into a table of counts from another container.
            kg = _sheet("TSTU0000000", [{"group": "1", "values": {"sound": 0.5}, "stated_total": 0.5}],
                        unit="kg", cats=build_categories("GRAPE"))
            res = await ac.post(url, json={**kg, "block_id": apple["id"]}, headers=hdr)
            assert res.status_code == 422

            # The grapes sheet goes into the grapes table.
            gsheet = _sheet(C1, [{"group": "Box 1", "values": {"sound": 0.82, "soft": 0.18}, "stated_total": 1.0}],
                            unit="kg", cats=build_categories("GRAPE"))
            res = await ac.post(url, json={**gsheet, "block_id": "b_table_grape"}, headers=hdr)
            assert res.status_code == 200, res.text
            g = next(b for b in res.json()["block_state"]["blocks"] if b["id"] == "b_table_grape")
            assert g["rows"][0]["values"]["sound"] == "0.820"
            # Column off: the sheet's container is not stamped on the rows.
            assert "container" not in g["rows"][0]

            # Both tables print.
            res = await ac.get(f"/api/reports/{rid}/preview/html", headers=hdr)
            assert res.status_code == 200, res.text[:500]
            assert f"<td>{C2}</td>" in res.text and "0.820" in res.text
        finally:
            await ac.delete(f"/api/reports/{rid}", headers=hdr)
