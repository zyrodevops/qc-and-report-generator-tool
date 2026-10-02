"""
General cargo reports in the client's layout.

Final only. Cover fields that can be changed, the sections in his order,
PARAGRAPH numbers worked out from what is included, and one OUR SURVEY
paragraph per container or visit. Nothing is written in on his behalf.
"""

import io
import json
import re

import docx
import pytest
from httpx import ASGITransport, AsyncClient

from app.compute.arithmetic import compute
from app.main import app
from app.render.docx.engine import render_docx
from app.render.html.engine import render_html
from app.seeds import general_cargo as gcmod
from app.seeds.defaults import get_default_block_state


def _state(mode="SEA"):
    return get_default_block_state(f"general_cargo_{mode.lower()}_survey", "STEEL_METALS")


def _by_id(state):
    return {b["id"]: b for b in state["blocks"]}


def test_layout_is_his_and_starts_empty():
    s = _state()
    assert s["report_title"] == "FINAL SURVEY REPORT"
    assert s["metadata"]["report_kind"] == "general_cargo" and s["metadata"]["state"] == "FINAL"
    assert s["metadata"]["cargo_label"] == "Steel & metal"
    assert [b["type"] for b in s["blocks"]] == [
        "particulars", "narrative", "attendance", "narrative", "gc_table", "survey_unit",
        "narrative", "gc_table", "narrative", "gc_table", "narrative", "photo_plate", "fixed_text"]
    # No wording, no tables of figures, nothing that stands for facts.
    for b in s["blocks"]:
        if b["type"] in ("narrative", "survey_unit"):
            assert b["additional_text"] == ""
    assert not any(b["type"] == "table" for b in s["blocks"])
    labels = [r["label"] for r in _by_id(s)["b_particulars"]["rows"]]
    assert labels[:5] == ["Insurers", "Policy No.", "Insured Value", "Shipper", "Consignees"]
    assert "Bill of Lading No. & Date" in labels and "Container Nos." in labels
    # every value starts as a visible blank, flagged before download
    assert all(re.fullmatch(r"\[.+\]", r["value"][0]) for r in _by_id(s)["b_particulars"]["rows"])
    air = [r["label"] for r in _by_id(_state("AIR"))["b_particulars"]["rows"]]
    assert "Air Waybill No. & Date" in air and "Container Nos." not in air
    # his own closing
    assert "We reserve the right to modify or add to this report" in _by_id(s)["b_closure"]["content"]
    assert "ISSUED WITHOUT PREJUDICE" in _by_id(s)["b_closure"]["content"]


def test_no_other_firms_name_in_the_layout():
    text = json.dumps(_state()) + json.dumps(gcmod.CARGO_TYPES) + json.dumps(gcmod.OPTIONAL_COVER_FIELDS)
    assert not re.search(r"gladstone|\bG[/-]\d{3,4}[/-]\d{2}", text, re.I)


def test_paragraph_numbers_follow_what_is_included():
    s = _state()
    b = _by_id(s)
    unit2 = gcmod.survey_unit(2, container="TSTU1234565", survey_date="22 June 2026", place="the CFS")
    s["blocks"].insert(s["blocks"].index(b["b_survey_1"]) + 1, unit2)
    b["b_survey_1"].update(survey_date="21 June 2026", joint=True)
    heads = {x["id"]: x.get("_heading") for x in compute(s)["blocks"]}
    assert heads["b_application"] == "PARAGRAPH 1: APPLICATION:"
    assert heads["b_circumstances"] == "PARAGRAPH 2: CIRCUMSTANCES OF LOSS:"
    assert heads["b_survey_1"] == "PARAGRAPH 2.1: OUR JOINT SURVEY ON 21 JUNE 2026:"
    assert heads["b_survey_2"] == "PARAGRAPH 2.2: OUR SURVEY ON 22 JUNE 2026 AT THE CFS FOR CONTAINER NO. TSTU1234565:"
    assert heads["b_cause"] == "PARAGRAPH 3: CAUSE OF LOSS:" and heads["b_documentation"] == "PARAGRAPH 5: DOCUMENTATION:"
    # a section left out: no gap
    b["b_next_step"]["included"] = False
    heads = {x["id"]: x.get("_heading") for x in compute(s)["blocks"]}
    assert heads["b_documentation"] == "PARAGRAPH 4: DOCUMENTATION:"
    # fruit reports keep the numbers in their names
    fruit = get_default_block_state("perishable_sea_survey", "APPLE")
    assert not any(x.get("_heading") for x in compute(fruit)["blocks"])


def test_word_and_html():
    s = _state()
    b = _by_id(s)
    b["b_application"]["additional_text"] = "The consignees vide their email informed us."
    b["b_attendance"]["rows"] = [{"name": "Mr. A", "designation": "Manager", "representing": "Consignees"},
                                 {"name": "", "designation": "", "representing": ""}]
    b["b_survey_1"].update(survey_date="22 June 2026", container="TSTU1234565",
                           additional_text="We visited the CFS on 22 June 2026.\n\n• Seal found intact.\n• Doors sound.",
                           attendance=[{"name": "Mr. B", "designation": "CHA", "representing": "Consignees"}])
    d = docx.Document(io.BytesIO(render_docx(s)))
    paras = [p.text for p in d.paragraphs]
    assert "PARTICULARS" not in paras  # the cover has no heading of its own
    assert "PARAGRAPH 1: APPLICATION:" in paras
    assert "The following persons attended the survey:" in paras
    heading = paras.index("PARAGRAPH 2.1: OUR SURVEY ON 22 JUNE 2026 FOR CONTAINER NO. TSTU1234565:")
    body = paras[heading + 1:]
    # the visit's people come after its first paragraph
    assert body[0] == "We visited the CFS on 22 June 2026."
    assert body[1] == "The following persons attended the survey:"
    assert "Seal found intact." in body
    att = [t for t in d.tables if t.rows[0].cells[0].text == "Name"]
    assert len(att) == 2 and len(att[0].rows) == 2  # the empty row is left out

    h = render_html(s)
    assert "PARAGRAPH 2.1: OUR SURVEY ON 22 JUNE 2026 FOR CONTAINER NO. TSTU1234565:" in h
    assert "Attendance at Survey" not in h and h.count("The following persons attended the survey:") == 2


def test_findings_print_as_the_damage_table_where_it_is_marked():
    s = _state()
    unit = _by_id(s)["b_survey_1"]
    unit["additional_text"] = "The details are as follows:\n\n(damage table)\n\nThe rest of the bags were found sound."
    unit["findings"] = [{"item": "bags", "total": "500", "affected": "45", "condition": "wet", "photos": "5 to 9"},
                        {"item": "", "total": "", "affected": "", "condition": "", "photos": ""}]
    unit["findings"] += [{"item": f"drum {i}", "total": "", "affected": "1", "condition": "dented", "photos": ""}
                         for i in range(10)]
    rows = compute(s)["blocks"][[b["id"] for b in s["blocks"]].index("b_survey_1")]["_computed"]["findings_rows"]
    assert rows[0] == ["1", "bags", "45 of 500", "wet", "5 to 9"] and len(rows) == 11  # the empty line left out
    assert rows[-1][0] == "11"  # Sr. No. above 9 is computed, so the check on printed numbers finds it

    d = docx.Document(io.BytesIO(render_docx(s)))
    body = d.element.body
    paras = [p.text for p in d.paragraphs]
    assert "(damage table)" not in paras
    table = next(t for t in d.tables if t.rows[0].cells[0].text == "Sr. No.")
    assert [c.text for c in table.rows[0].cells] == gcmod.DAMAGE_TABLE_COLUMNS
    assert [c.text for c in table.rows[1].cells] == ["1", "bags", "45 of 500", "wet", "5 to 9"]
    # between the text before the mark and the text after it
    order = [el.tag.split("}")[1] + ":" + ("".join(el.itertext())[:30]) for el in body.iterchildren()]
    i_before = next(i for i, o in enumerate(order) if "The details are as follows" in o)
    i_table = next(i for i, o in enumerate(order) if o.startswith("tbl:Sr. No."))
    i_after = next(i for i, o in enumerate(order) if "The rest of the bags" in o)
    assert i_before < i_table < i_after

    h = render_html(s)
    assert "damage-table" in h and "45 of 500" in h and "(damage table)" not in h
    # ticked off: no table
    unit["findings_table"] = False
    assert "damage-table" not in render_html(s)


@pytest.mark.asyncio
async def test_created_as_preliminary_when_picked_and_documents_fill_his_cover_fields():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        tok = (await ac.post("/api/auth/login", json={"password": "surveyor123"})).json()["token"]
        hdr = {"Authorization": f"Bearer {tok}"}
        res = await ac.post("/api/reports", json={"family": "SURVEY_REPORT", "commodity": "MACHINERY_PARTS",
                                                   "template_id": "general_cargo_sea_survey", "state": "PRELIMINARY"},
                            headers=hdr)
        assert res.status_code == 201, res.text
        rep = res.json()
        rid = rep["id"]
        try:
            # Preliminary when picked: same layout, its own title
            assert rep["state"] == "PRELIMINARY"
            assert rep["block_state"]["report_title"] == "PRELIMINARY SURVEY REPORT"
            assert rep["block_state"]["metadata"]["state"] == "PRELIMINARY"
            assert rep["block_state"]["metadata"]["cargo_label"] == "Machinery & equipment"
            res = await ac.post(f"/api/reports/{rid}/documents/apply", headers=hdr, json={
                "particulars": [{"label": "Exporter / Shipper", "value": "Shipper Co, Germany"},
                                {"label": "Consignee", "value": "Buyer Pvt Ltd, India"},
                                {"label": "Cargo Declared", "value": "22 Packages of Machinery"}],
                "shipment": {}})
            assert res.status_code == 200, res.text
            rows = {r["label"]: r["value"][0] for r in
                    next(b for b in res.json()["block_state"]["blocks"] if b["type"] == "particulars")["rows"]}
            assert rows["Shipper"] == "Shipper Co, Germany" and rows["Consignees"] == "Buyer Pvt Ltd, India"
            assert rows["Consignment"] == "22 Packages of Machinery"
            assert "Exporter / Shipper" not in rows and "Cargo Declared" not in rows
        finally:
            await ac.delete(f"/api/reports/{rid}", headers=hdr)

        res = await ac.get("/api/commodities", params={"category": "GENERAL_CARGO"})
        cats = res.json()["commodities"]
        assert {c["key"] for c in cats} == gcmod.CARGO_TYPE_KEYS
        assert all(c["defect_columns"] == [] and c["top_narrative_clauses"] == [] for c in cats)
