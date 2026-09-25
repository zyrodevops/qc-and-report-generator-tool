"""
Reading shipment documents without AI.

Every document here is a small PDF built in the test, with made-up parties and
container numbers. The client's documents are not in the repository.
"""

import pytest
from httpx import ASGITransport, AsyncClient

from app.ingest.documents.merge import merge, particulars, title
from app.ingest.documents.readers import (
    classify, containers_in, iso6346_ok, read_document, read_recorder, written_date,
)
from app.main import app
from app.seeds.clause_library import bind


# ---------------------------------------------------------------------------
# A tiny PDF writer: text and boxes, enough to look like a shipping form
# ---------------------------------------------------------------------------

def make_pdf(pages):
    """pages: [[("text", x, y, "words") | ("box", x, y, w, h) | ("line", x0, y0, x1, y1)]], y from the top."""
    H = 842
    objs = []

    def esc(s):
        return s.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")

    page_ids = []
    font_id = 3
    objs.append(None)  # 1 catalog
    objs.append(None)  # 2 pages
    objs.append(b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>")
    for ops in pages:
        content = []
        for op in ops:
            if op[0] == "text":
                _, x, y, s = op
                content.append(f"BT /F1 8 Tf 1 0 0 1 {x} {H - y} Tm ({esc(s)}) Tj ET")
            elif op[0] == "box":
                _, x, y, w, h = op
                content.append(f"{x} {H - y - h} {w} {h} re S")
            elif op[0] == "line":
                _, x0, y0, x1, y1 = op
                content.append(f"{x0} {H - y0} m {x1} {H - y1} l S")
        stream = "\n".join(content).encode("latin-1")
        objs.append(b"<< /Length %d >>\nstream\n" % len(stream) + stream + b"\nendstream")
        content_id = len(objs)
        objs.append(f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 {H}] /Contents {content_id} 0 R "
                    f"/Resources << /Font << /F1 {font_id} 0 R >> >> >>".encode())
        page_ids.append(len(objs))
    objs[0] = b"<< /Type /Catalog /Pages 2 0 R >>"
    objs[1] = f"<< /Type /Pages /Kids [{' '.join(f'{i} 0 R' for i in page_ids)}] /Count {len(page_ids)} >>".encode()
    out = bytearray(b"%PDF-1.4\n")
    offsets = []
    for i, o in enumerate(objs, 1):
        offsets.append(len(out))
        out += f"{i} 0 obj\n".encode() + o + b"\nendobj\n"
    xref = len(out)
    out += f"xref\n0 {len(objs) + 1}\n0000000000 65535 f \n".encode()
    for off in offsets:
        out += f"{off:010d} 00000 n \n".encode()
    out += f"trailer\n<< /Size {len(objs) + 1} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF".encode()
    return bytes(out)


def container(owner="TSTU", serial="123456"):
    """A made-up container number with a correct check digit."""
    for d in range(10):
        if iso6346_ok(owner, serial, str(d)):
            return f"{owner}{serial}{d}"


C1, C2 = container("TSTU", "123456"), container("FAKU", "765432")


def bill_of_lading(seal2="SL20002"):
    return make_pdf([[
        ("box", 1, 10, 280, 12), ("text", 5, 19, "SHIPPER"),
        ("text", 5, 34, "GREEN VALLEY ORCHARDS DE CHILE"), ("text", 5, 44, "12 FRUIT ROAD, TALCA, CHILE"),
        ("box", 1, 80, 280, 12), ("text", 5, 89, "CONSIGNEE"),
        ("text", 5, 104, "EXAMPLE FRESH IMPORTS PVT LTD"), ("text", 5, 114, "PLOT 7, VASHI, MAHARASHTRA, INDIA"),
        ("box", 1, 150, 280, 12),
        ("box", 492, 6, 96, 13), ("text", 511, 15, "VOYAGE NUMBER"), ("text", 512, 30, "123E"),
        ("box", 492, 37, 96, 13), ("text", 500, 46, "BILL OF LADING NUMBER"), ("text", 512, 61, "TST0001234"),
        ("box", 1, 257, 591, 9), ("line", 133, 230, 133, 284), ("line", 282, 230, 282, 284),
        ("line", 434, 230, 434, 284), ("box", 1, 230, 592, 81),
        ("text", 55, 264, "VESSEL"), ("text", 170, 264, "PORT OF LOADING"), ("text", 320, 264, "PORT OF DISCHARGE"),
        ("text", 2, 276, "SEA BREEZE"), ("text", 135, 276, "VALPARAISO, CHILE"), ("text", 284, 276, "NHAVA SHEVA"),
        ("box", 1, 284, 591, 27),
        ("text", 2, 330, f"{C1}  1x40RH 1000 CARTON  20500.000 4300 60.000"),
        ("text", 2, 340, "SEAL SL10001"),
        ("text", 2, 360, f"{C2}  1x40RH 1000 CARTON  20500.000 4300 60.000"),
        ("text", 2, 370, f"SEAL {seal2}"),
        ("text", 100, 390, "Cargo is stowed in a refrigerated container set at the shipper's requested"),
        ("text", 100, 400, "carrying temperature of 0 degrees Celsius"),
        ("text", 100, 410, "TOTAL NET WEIGHT: 36.000,000 KGS"),
        ("text", 100, 420, "TOTAL GROSS WEIGHT: 41.000,000 KGS"),
        ("text", 100, 430, "2000 CARTONS WITH FRESH APPLES"),
        ("text", 100, 450, "Shipped on Board SEA BREEZE 02-MAR-2026"),
        ("text", 1, 470, "PLACE AND DATE OF ISSUE SAN ANTONIO    02 MAR 2026"),
        ("text", 1, 480, "BILL OF LADING"),
    ]])


def packing_list(cno, seal):
    return make_pdf([[("text", 20, 20, "PACKING LIST"), ("text", 20, 40, f"Container: {cno}  SEAL: {seal}"),
                      ("text", 20, 60, "PORT OF LOADING: Valparaiso/Chile"), ("text", 20, 80, "PORT OF DISCHARGE: NHAVA SHEVA, INDIA")]])


RECORDER_TEXT = [
    "Data Report Data Logger", "Logging Summary",
    "Note:All times shown are based on UTC and 24-Hour clock [MM/DD/YY HH:MM:SS]-03:00",
    "Device ID: 111111111A Log Interval/cycle: 10 min",
    "Start Time/First Point: 03/02/26 10:00:00 Highest Temperature:6.5",
    "Lowest Temperature: -0.5 Stop Time: 03/02/26 10:30:00",
    "Average Temperature:1.0 Data Point: 4", "Mean Kinetic Temperature: 2.0 Trip Length: 0d0h30m",
    "03/02/26 10:00:00 03/05/26 12:00:00",  # the chart's axis labels: not readings
    "03/02/26 10:00:00 -0.5", "03/02/26 10:10:00 0.2", "03/02/26 10:20:00 6.5", "03/02/26 10:30:00 0.8",
    f"Container {C1}",
]


def recorder_pdf():
    return make_pdf([[("text", 20, 20 + 12 * i, s) for i, s in enumerate(RECORDER_TEXT)]])


# ---------------------------------------------------------------------------

def test_container_numbers_need_their_check_digit():
    assert containers_in(f"cargo in {C1} and {C1[:-1]}9") == [C1] if not C1.endswith("9") else True
    assert containers_in("RUC6BR0158754120632026") == []


def test_dates_in_words_only():
    assert written_date("02-MAR-2026") == "2 March 2026"
    assert written_date("16 MAY 2026") == "16 May 2026"
    assert written_date("28-May-26") == "28 May 2026"
    assert written_date("04/05/2026") is None  # April or May: not guessed


def test_what_a_document_is():
    assert classify("") == "scanned"
    assert classify("JOINT SURVEY REPORT ... BILL OF LADING SSZ...") == "other_report"
    assert classify("Data Report Data Logger Logging Summary Trip Length: 3d") == "recorder"
    body = " Shipper Consignee Port of Loading Port of Discharge Description of goods"
    assert classify("SEA WAYBILL" + body) == "sea_waybill"
    assert classify("AIR WAYBILL Airport of Departure" + body) == "air_waybill"
    assert classify("COMMERCIAL INVOICE Inv. Number" + body) == "invoice"


def test_bill_of_lading_is_read_from_its_boxes():
    r = read_document(bill_of_lading(), "bl.pdf")
    f = {k: v["value"] for k, v in r["fields"].items()}
    assert r["kind"] == "bill_of_lading" and r["mode"] == "SEA"
    assert f["shipper"][0] == "GREEN VALLEY ORCHARDS DE CHILE"
    assert f["consignee"][0] == "EXAMPLE FRESH IMPORTS PVT LTD"
    assert f["vessel"] == "SEA BREEZE" and f["voyage"] == "123E"
    assert f["document_number"] == "TST0001234"
    assert f["port_of_loading"] == "VALPARAISO, CHILE" and f["port_of_discharge"] == "NHAVA SHEVA"
    assert f["requested_temperature_c"] == ["0"]
    assert f["issue_date"] == "2 March 2026" and f["shipped_on_board_date"] == "2 March 2026"
    assert [(c["container"], c["seal"], c["packages"]) for c in r["containers"]] == [
        (C1, "SL10001", "1000 CARTON"), (C2, "SL20002", "1000 CARTON")]


def test_recorder_is_read_exactly():
    r = read_recorder(recorder_pdf(), "Annexure A.pdf")
    s = r["summary"]
    assert s["device_id"] == "111111111A" and s["highest_c"] == "6.5" and s["date_order"] == "MDY"
    assert [v for _, v in r["readings"]] == [-0.5, 0.2, 6.5, 0.8]  # the axis labels are not counted
    assert r["readings"][0][0] == "2026-03-02T10:00:00"
    assert s["container"] == C1


def test_documents_are_checked_against_each_other():
    docs = [
        {**read_document(bill_of_lading(), "bl.pdf"), "filename": "bl.pdf"},
        {**read_document(packing_list(C2, "SL99999"), "pl2.pdf"), "filename": "pl2.pdf"},
        {**read_document(recorder_pdf(), "rec.pdf"), "filename": "rec.pdf"},
    ]
    m = merge(docs)
    ship = m["shipment"]
    assert ship["mode"] == "SEA" and ship["requested_temperature_c"] == "0"
    # The packing list's seal differs from the B/L's: shown, not settled.
    assert any(c["field"] == f"Seal of {C2}" for c in m["conflicts"])
    assert next(c for c in ship["containers"] if c["container"] == C2)["seal"] == "SL20002"
    assert ship["recorders"][0]["container"] == C1
    rows = {r["label"]: r["value"] for r in particulars(ship)}
    assert rows["Exporter / Shipper"] == "Green Valley Orchards De Chile, Chile"
    assert rows["Consignee"] == "Example Fresh Imports Pvt Ltd, Maharashtra, India"
    assert rows["Bill of Lading / AWB No."] == "TST0001234 dated 2 March 2026"
    assert rows["Carrying Vessel / Flight"] == "“SEA BREEZE” Voy No. 123E"
    assert rows["Port of Loading"] == "Valparaiso, Chile"
    assert rows["Net / Gross Weight"] == "Net 36,000 kg / Gross 41,000 kg"
    assert rows["Container / Carriage Unit"].endswith("(2 × 40' Reefers)")


def test_names_keep_their_acronyms():
    assert title("NGK TRADING PVT LTD") == "NGK Trading Pvt Ltd"
    assert title("NAVEGANTES, SC, BRAZIL") == "Navegantes, SC, Brazil"


def test_requested_temperature_fills_only_the_bl_sentence():
    assert bind("As per the Bill of Lading, the requested temperature for this shipment was [NUMBER]°C.",
                {"requested_temp": "0"}).endswith("was 0°C.")
    advice = "The consignees have informed us that fruits must be stored at a temperature of [NUMBER]°C to [NUMBER]°C"
    assert bind(advice, {"requested_temp": ["2", "8"]}) == advice


@pytest.mark.asyncio
async def test_read_then_apply_fills_the_particulars():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        login = await ac.post("/api/auth/login", json={"password": "surveyor123"})
        hdr = {"Authorization": f"Bearer {login.json()['token']}"}
        rep = (await ac.post("/api/reports", json={"family": "SURVEY_REPORT", "commodity": "APPLE",
                                                   "template_id": "perishable_sea_survey"}, headers=hdr)).json()
        res = await ac.post(f"/api/reports/{rep['id']}/documents/read", headers=hdr,
                            files=[("files", ("bl.pdf", bill_of_lading(), "application/pdf")),
                                   ("files", ("rec.pdf", recorder_pdf(), "application/pdf")),
                                   ("files", ("notes.txt", b"hello", "text/plain"))])
        assert res.status_code == 200, res.text
        body = res.json()
        assert [d["kind"] for d in body["documents"]] == ["bill_of_lading", "recorder", "unsupported"]
        # Nothing is in the report until it is applied.
        st = (await ac.get(f"/api/reports/{rep['id']}", headers=hdr)).json()["block_state"]
        assert "shipment" not in st["metadata"]
        res = await ac.post(f"/api/reports/{rep['id']}/documents/apply", headers=hdr,
                            json={"particulars": body["particulars"], "shipment": body["shipment"]})
        assert res.status_code == 200, res.text
        st = res.json()["block_state"]
        p = next(b for b in st["blocks"] if b["type"] == "particulars")
        row = next(r for r in p["rows"] if r["label"] == "Port of Discharge")
        assert row["value"] == ["Nhava Sheva"] and row["provenance"] == "document_verified"
        assert st["metadata"]["shipment"]["requested_temperature_c"] == "0"
        assert st["metadata"]["recorders"][0]["container"] == C1


@pytest.mark.asyncio
async def test_recorders_get_a_summary_section_and_a_graph_that_can_be_left_out():
    from docx import Document
    import io as _io

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        login = await ac.post("/api/auth/login", json={"password": "surveyor123"})
        hdr = {"Authorization": f"Bearer {login.json()['token']}"}
        rep = (await ac.post("/api/reports", json={"family": "SURVEY_REPORT", "commodity": "APPLE",
                                                   "template_id": "perishable_sea_survey"}, headers=hdr)).json()
        body = (await ac.post(f"/api/reports/{rep['id']}/documents/read", headers=hdr,
                              files=[("files", ("bl.pdf", bill_of_lading(), "application/pdf")),
                                     ("files", ("rec.pdf", recorder_pdf(), "application/pdf"))])).json()
        st = (await ac.post(f"/api/reports/{rep['id']}/documents/apply", headers=hdr,
                            json={"particulars": body["particulars"], "shipment": body["shipment"]})).json()["block_state"]
        types = [b["type"] for b in st["blocks"]]
        rb = next(b for b in st["blocks"] if b["type"] == "temperature_recorders")
        # Straight after the cause of loss, where the printouts are discussed.
        assert st["blocks"][types.index("temperature_recorders") - 1].get("section", "").upper().endswith("CAUSE OF LOSS")
        rec = rb["recorders"][0]
        assert (rec["device_id"], rec["highest_c"], rec["container"]) == ("111111111A", "6.5", C1)
        assert rb["set_point_c"] == "0" and rb["show_chart"] is True

        png = await ac.get(f"/api/reports/{rep['id']}/recorders/{rec['asset_id']}/chart.png", headers=hdr)
        assert png.status_code == 200 and png.content.startswith(bytes([0x89]) + b"PNG")
        ac.cookies.clear()  # the login set a session cookie; without it the graph is refused
        assert (await ac.get(f"/api/reports/{rep['id']}/recorders/{rec['asset_id']}/chart.png")).status_code == 401

        from app.render.docx.engine import render_recorders
        doc = Document()
        render_recorders(doc, rb)
        assert doc.tables[0].rows[1].cells[0].text == "111111111A"
        assert len(doc.inline_shapes) == 1
        doc = Document()
        render_recorders(doc, {**rb, "show_chart": False})
        assert len(doc.inline_shapes) == 0 and len(doc.tables) == 1
