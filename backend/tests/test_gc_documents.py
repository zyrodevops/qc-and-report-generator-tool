"""
General cargo documents: bundles split into their documents, the new kinds
read, the scans read by the online reader (faked here), and all of it put
into the cover, the seals table and the survey paragraphs.

Every document is made up for the test. The client's documents are not in the
repository.
"""

import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(__file__))
from test_shipment_documents import container, make_pdf  # noqa: E402

from app.api.documents import _apply_weight_slips, _fill_seals_table, tare_is_of
from app.config import settings
from app.ingest.documents import gc_readers as g
from app.ingest.documents.merge import merge, particulars
from app.ingest.documents.pages import split, title_kind
from app.ingest.documents.readers import read_file
from app.ingest.tally import cloud_reader
from app.seeds.defaults import get_default_block_state
from app.services import scan_reader

C1, C2 = container("TSTU", "111111"), container("FAKU", "222222")

INSURANCE = f"""Example General Insurance Company Limited 12345
Certificate of Insurance cum Policy Schedule
Policy No. 1111 2222 3333 Marine Cargo Insurance
Insured Name : : M/S. TEST TRADERS
Policy Issuance Date : : 03/04/2026
Sum Insured in Invoice Currency Rate of Exchange Sum Insured in INR Basis of Valuation
USD 1,10,000.00 90.00 99,00,000.00 Invoice value + 10%"""
BILL_OF_ENTRY = f"""Port Code BE No BE Date BE Type
INNSA1 1234567 24/05/2026 H
PORT : CB NAME TEST CLEARING AGENTS
BILL OF ENTRY FOR HOME CONSUMPTION
1.IGM NO 2.IGM DATE 3.INW DATE
7654321 04/05/2026 21/05/2026 0
1 F SEAL001 {C1}
2 F SEAL002 {C2}"""
EIR = f"""Test Freeport Terminal
EQUIPMENT INTERCHANGE REPORT
DELIVER IMPORT CONTAINER
Container No: {C1}
Dest/ POD2: TEST CFS PVT LTD
In Date: 27/05/2026 04:54
Out Date: 27/05/2026 06:21
Seal 1: SEAL001
Truck No: MH01AB1234
Remarks:"""
TRACKING = f"""Tracking details CONTAINER TO CONSIGNEE
Date Moves Location Vessel (Voyage)
{C1} 22 G1 (20ST)
Wednesday,11-MAR-2026 01:18 PM EMPTY TO SHIPPER TEST CITY
Thursday,19-MAR-2026 11:48 AM LOADED ON BOARD TEST PORT TEST VESSEL
Thursday,21-MAY-2026 11:12 PM VESSEL ARRIVAL NHAVA SHEVA OTHER VESSEL
Friday,22-MAY-2026 05:14 AM DISCHARGED NHAVA SHEVA OTHER VESSEL
Wednesday,27-MAY-2026 10:34 PM CONTAINER TO CONSIGNEE NHAVA SHEVA"""
INVOICE = """COMMERCIAL INVOICE
COMMERCIAL INVOICE NO.: TST/2026/001 DATE: 20-Mar-2026
BILL OF LADING NUMBER: TSTBL0001
QUANTITY PRICE TOTAL AMOUNT
STEEL COILS 50.000 $1,000.00 $50,000.00
LESS: ADVANCE PAYMENT RECEIVED ($10,000.00)
TOTAL 50.000 $40,000.00"""
PACKING = f"""PACKING LIST
CONTAINER NUMBER SEAL NUMBER NET WEIGHT GROSS WEIGHT
STEEL {C1} SEAL001 20.765 M.T. 20.900 M.T.
{C2} SEAL002 21.010 M.T. 21.150 M.T.
TOTAL 41.775 M.T. 42.050 M.T."""


# ---------------------------------------------------------------------------
# What a page is, and a bundle split into its documents
# ---------------------------------------------------------------------------

def test_a_page_is_what_its_title_says():
    assert title_kind(INSURANCE) == "insurance"
    assert title_kind(BILL_OF_ENTRY) == "bill_of_entry"
    assert title_kind("Port Code SB No SB Date\nINNSA1 1234 02-MAY-26 ... BILL OF ENTRY FOR HOME CONSUMPTION") == "shipping_bill"
    assert title_kind(EIR) == "eir"
    assert title_kind(TRACKING) == "container_tracking"
    assert title_kind("From: Someone <a@b.c>\nSent: 11 May 2026 10:06\nTo: x\nSubject: documents") == "email"
    # an invoice that mentions the B/L is an invoice
    assert title_kind(INVOICE) == "invoice"
    # a packing list whose title is at the end of a long line, and which says "as per invoice"
    assert title_kind("Test Exports Ltd.\nPlot 7, Some Road, Some City, Maharashtra, India. PACKING LIST\nAS PER INVOICE") == "packing_list"
    # running text that uses the word is not a title: the page continues the one before
    assert title_kind("parties. The buyer will pay the invoice within 30 days of the date of the bill of lading.") is None


def test_a_bundle_is_split_into_its_documents():
    texts = [INSURANCE, "Special Conditions: the insured must take reasonable care of the goods at all times.",
             INVOICE, PACKING, "", "", BILL_OF_ENTRY, EIR, TRACKING]
    parts = split(texts)
    assert [(p.kind, p.pages) for p in parts] == [
        ("insurance", [1, 2]), ("invoice", [3]), ("packing_list", [4]), ("scanned", [5, 6]),
        ("bill_of_entry", [7]), ("eir", [8]), ("container_tracking", [9])]
    # a scanned file takes its kind from its name
    assert [p.kind for p in split(["", ""], "CFS Weight Slips.pdf")] == ["weight_slip"]


def test_read_file_splits_a_real_pdf_and_says_which_pages():
    def page(text):
        return [("text", 20, 20 + 12 * i, line) for i, line in enumerate(text.splitlines())]

    pdf = make_pdf([page(INSURANCE), page(INVOICE), [], page(TRACKING)])
    docs = read_file(pdf, "Documents.pdf")
    assert [(d["kind"], d.get("page_range")) for d in docs] == [
        ("insurance", "p1"), ("invoice", "p2"), ("scanned", "p3"), ("container_tracking", "p4")]
    assert docs[2]["scan"] is True
    assert docs[0]["fields"]["insurer"]["value"] == "Example General Insurance Company Limited"


# ---------------------------------------------------------------------------
# The readers
# ---------------------------------------------------------------------------

def test_insurance():
    f = {k: v["value"] for k, v in g.read_insurance([INSURANCE])["fields"].items()}
    assert f["insurer"] == "Example General Insurance Company Limited"
    assert f["policy_number"] == "1111 2222 3333"
    assert f["assured"] == "TEST TRADERS"
    assert f["insured_value"] == "USD 1,10,000.00 (INR 99,00,000.00)"
    assert f["issue_date"] == "3 April 2026"


def test_bill_of_entry_with_its_seals():
    d = g.read_bill_of_entry([BILL_OF_ENTRY])
    f = {k: v["value"] for k, v in d["fields"].items()}
    assert (f["be_number"], f["be_date"], f["inward_date"]) == ("1234567", "24 May 2026", "21 May 2026")
    assert f["customs_broker"] == "TEST CLEARING AGENTS"
    assert d["containers"] == [{"container": C1, "seal": "SEAL001"}, {"container": C2, "seal": "SEAL002"}]


def test_eir_and_tracking():
    e = g.read_eir([EIR])["eirs"][0]
    assert e["container"] == C1 and e["destination"] == "TEST CFS PVT LTD" and e["truck"] == "MH01AB1234"
    t = g.read_tracking([TRACKING])["tracking"][0]
    assert (t["loaded_on_board"], t["arrival"], t["discharged"], t["to_consignee"]) == (
        "19 March 2026", "21 May 2026", "22 May 2026", "27 May 2026")


def test_invoice_value_is_the_value_not_the_balance():
    assert g.invoice_value([INVOICE]) == "USD 50,000.00"
    assert g.invoice_value(["Net Receivable (₹) : 3,65,334.00"]) == "INR 3,65,334.00"
    assert g.invoice_value(["Invoice Value 81,349.17 USD 7,524,798.23 INR"]) == "USD 81,349.17"


def test_packing_list_weights_per_container():
    w = {x["container"]: x for x in g.container_weights([PACKING])}
    assert (w[C1]["net_kg"], w[C1]["gross_kg"]) == ("20765", "20900")
    assert g.total_weights(["TOTAL NET WEIGHT : 8900 TOTAL GROSS WEIGHT : 9500"]) == {
        "total_net_kg": "8900", "total_gross_kg": "9500"}


# ---------------------------------------------------------------------------
# Put together, and into the report
# ---------------------------------------------------------------------------

def _docs():
    ins = {"filename": "ins", **g.read_insurance([INSURANCE])}
    boe = {"filename": "boe", **g.read_bill_of_entry([BILL_OF_ENTRY])}
    eir = {"filename": "eir", **g.read_eir([EIR])}
    trk = {"filename": "trk", **g.read_tracking([TRACKING])}
    pl = {"filename": "pl", "kind": "packing_list", "container_weights": g.container_weights([PACKING])}
    inv = {"filename": "inv", "kind": "invoice", "fields": {"invoice_value": {"value": "USD 50,000.00"}}}
    return [ins, boe, eir, trk, pl, inv]


def test_the_cover_of_a_general_cargo_report():
    ship = merge(_docs())["shipment"]
    rows = {r["label"]: r["value"] for r in particulars(ship, general_cargo=True)}
    assert rows["Insurers"] == "Example General Insurance Company Limited"
    assert rows["Policy No."] == "1111 2222 3333" and rows["Insured Value"].startswith("USD 1,10,000.00")
    assert rows["Invoice Value"] == "USD 50,000.00"
    assert rows["Bill of Entry No. & Date"] == "1234567 dated 24 May 2026"
    assert rows["Discharged Date"] == "22 May 2026" and rows["Cargo Departed from CFS"] == "27 May 2026"
    assert ship["cfs"] == "TEST CFS PVT LTD"
    c1 = next(c for c in ship["containers"] if c["container"] == C1)
    assert c1["seal"] == "SEAL001" and c1["pl_gross_kg"] == "20900" and c1["tracking"]["discharged"] == "22 May 2026"
    # a fruit report's cover gets none of these
    assert "Insurers" not in {r["label"] for r in particulars(ship)}


def test_seals_table_and_weight_slips_go_into_the_report():
    state = get_default_block_state("general_cargo_sea_survey", "STEEL_METALS")
    ship = merge(_docs())["shipment"]
    for c in ship["containers"]:
        if c["container"] == C1:
            c["tare_kg"] = "2190"
    _fill_seals_table(state, ship)
    seals = next(b for b in state["blocks"] if b.get("kind") == "seals")
    assert [(r["container"], r["seal_doc"]) for r in seals["rows"]] == [(C1, "SEAL001"), (C2, "SEAL002")]

    slips = [{"container_no": C1, "weighbridge": "Test Weighbridge", "slip_no": "10001", "date": "22-06-2026",
              "gross_kg": "23100", "tare_kg": "2190", "net_kg": "20910"},
             {"container_no": C2, "gross_kg": "31000", "tare_kg": "9800", "net_kg": "21200", "tare_of": "truck"}]
    _apply_weight_slips(state, slips, ship["containers"])
    units = {u["container"]: u for u in state["blocks"] if u["type"] == "survey_unit"}
    # the first, empty paragraph takes the first container; a paragraph is added for the second
    assert set(units) == {C1, C2}
    w1 = units[C1]["weights"]
    # the slip's tare is the B/L tare: the container's
    assert (w1["gross"], w1["tare_container"], w1.get("tare_truck"), w1["declared"], w1["basis"]) == (
        "23100", "2190", None, "20900", "Packing List")
    assert units[C2]["weights"]["tare_truck"] == "9800"
    # figures already typed are kept
    units[C1]["weights"]["gross"] = "23150"
    _apply_weight_slips(state, slips[:1], ship["containers"])
    assert units[C1]["weights"]["gross"] == "23150"


def test_whose_tare():
    assert tare_is_of("2190", "2190") == "container" and tare_is_of("9800", "2190") == "truck"
    assert tare_is_of("2300", None) == "container" and tare_is_of("9800", None) == "truck"


# ---------------------------------------------------------------------------
# The online reader for scans (faked: no real call)
# ---------------------------------------------------------------------------

def test_a_read_slip_is_checked():
    ok = {"container_no": C1, "gross_kg": "23100", "tare_kg": "2190", "net_kg": "20910"}
    assert scan_reader.check_row("weight_slip", ok) == []
    bad = {"container_no": "ABCU1234567", "gross_kg": "23100", "tare_kg": "2190", "net_kg": "20000"}
    flags = scan_reader.check_row("weight_slip", bad)
    assert any("check digit" in f for f in flags) and any("≠ net" in f for f in flags)


@pytest.mark.asyncio
async def test_scans_are_read_and_the_reader_can_be_away(monkeypatch):
    monkeypatch.setattr(settings, "GEMINI_API_KEY", "test-key")

    async def answer(body):
        n = sum(1 for p in body["contents"][0]["parts"] if "inline_data" in p)
        return {"items": [{"image": i + 1, "container_no": C1, "gross_kg": "23,100 kg", "tare_kg": "2190",
                           "net_kg": "20910", "slip_no": str(100 + i)} for i in range(n)]}, "model-x", None

    monkeypatch.setattr(cloud_reader, "_race_models", answer)
    res = await scan_reader.read_scans("weight_slip", [(p, b"jpeg") for p in range(1, 8)])
    assert len(res["rows"]) == 7 and res["model"] == "model-x"   # two requests of 5 and 2
    assert res["rows"][0]["gross_kg"] == "23100" and res["rows"][0]["flags"] == []
    assert [r["page"] for r in res["rows"]] == list(range(1, 8))

    async def away(body):
        return None, None, "Today's free reading allowance is used up."

    monkeypatch.setattr(cloud_reader, "_race_models", away)
    res = await scan_reader.read_scans("weight_slip", [(1, b"jpeg")])
    assert "allowance" in res["error"] and res["rows"][0]["flags"] == ["not read"]

    monkeypatch.setattr(settings, "GEMINI_API_KEY", "")
    res = await scan_reader.read_scans("weight_slip", [(1, b"jpeg")])
    assert "not set up" in res["error"] and res["rows"] == []
