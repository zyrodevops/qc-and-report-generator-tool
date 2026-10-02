"""
General cargo wording: from the reports of the firm the client worked for,
with that firm's name, case numbers and letterhead never offered, and only
sentences used across several cases and years.

Every sentence here is made up for the test. The reports themselves are not
in the repository and must not be copied into it.
"""

import os
from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.seeds import gc_clause_library as gc

FIRM = "Gladstone"  # the other firm, as its reports print it


def _report(case, year, paras, mode="SEA", typ="final"):
    return {"case": case, "year": year, "type": typ, "mode": mode, "paragraphs": paras}


REQUEST = "We were asked by the consignees vide their email of 3 March 2021 and requested us to attend the damaged cargo."
NOTICE = "We advised the consignees to send notice of claim to the carriers and invite them for the joint survey."
STAGE = "However, the precise stage of damage could not be established from the papers produced before us."
ONE_PROJECT = "The empty container was found with the importer's own tarpaulin sheet spread over the steel coils."
LIGHT = "Light test was carried out by closing the doors of the container and no light was seen."
SOUND = "The container was found externally sound except for normal wear and tear at the time of survey."
FIRM_LINE = f"We, {FIRM} Agencies Limited, were appointed vide their email of 4 April 2022 and requested us to attend."
INTERIM = "A final report will be issued upon receipt of the documents requested from the consignees."
# the same idea, worded a little differently in each report, with its own facts
ARRIVALS = [
    "It was said to us that after landing from the vessel “Sea Star” Voy. No. 12W at Nhava Sheva Port on 3 May 2021, "
    "the subject 40’HC Container No. ABCU1234560 was shifted to Alpha Logistics Pvt. Ltd., Container Freight Station, "
    "Uran for customs formalities and delivery.",
    "It was said to us that after landing from the vessel “Blue Moon” Voy. No. 7E at Mundra Port on 9 June 2021, "
    "the subject 20’ Container No. DEFU7654320 was shifted to Beta Terminals Ltd. for customs formalities and delivery.",
    "It was said to us that after landing from the vessel “Red Sun” Voy. No. 45 at Nhava Sheva Port on 1 July 2022, "
    "the subject Container No. GHIU1111110 was shifted to Gamma CFS, Panvel for customs formalities and delivery.",
]
BAGS_WET = "On spot silver nitrate test was carried out on the wet bags and the result was found negative."


def _reports():
    out = []
    for i, year in enumerate((21, 21, 22)):
        out.append(_report(f"G-10{i}-{year}B", year, [
            "APPLICATION:", REQUEST, NOTICE, FIRM_LINE,
            "CIRCUMSTANCES OF LOSS:", ARRIVALS[i],
            "OUR SURVEY:", SOUND, LIGHT, INTERIM, f"• {BAGS_WET}", "The remaining bags were found in sound condition.",
            "CAUSE OF LOSS:", STAGE,
            "Page 2 of 4", f"{FIRM.upper()} AGENCIES LIMITED - Offices in several cities",
        ]))
    # one importer's project: five cases, all in one year
    for i in range(5):
        out.append(_report(f"G-20{i}-23B", 23, ["OUR SURVEY:", SOUND, ONE_PROJECT]))
    # a loading survey is not a source
    out.append(_report("G-300-24B", 24, ["OUR SURVEY:", "The lashing of the unit was checked by us on the trailer before departure."], typ="loading"))
    return out


def _rows(reports):
    return [r.as_row() for r in gc.build_topic_texts(reports)]


def test_headings_map_onto_the_clients_sections():
    secs = gc.split_sections(["Survey report no. 12", "1. INTRODUCTION:", REQUEST, "Circumstances of loss:", NOTICE,
                              "OUR JOINT SURVEY:", SOUND, "• Doors were found closed and sealed by the carrier.",
                              "• The seal was found intact when checked by us.", "PROBABLE CAUSE:", STAGE,
                              "NEXT STEPS:", "We have requested the consignees to keep us updated."])
    assert set(secs) == {"application", "circumstances_of_loss", "survey_findings", "cause_of_loss", "next_step"}
    # a run of list items stays one list
    assert "sealed by the carrier.\n• The seal" in secs["survey_findings"]


def test_the_firm_its_case_numbers_and_annexure_letters_are_taken_out():
    t = gc._scrub(f"{FIRM} Agencies Pvt. Ltd. ref G/1234/21B: copies attached as Annexure A & B.")
    assert FIRM.lower() not in t.lower() and "1234" not in t
    assert "Annexure [NUMBER]" in t
    assert gc.foreign(f"as per {FIRM} file") and gc.foreign("our ref G-567-22C") and not gc.foreign(t)


def test_a_sentence_needs_three_cases_and_more_than_one_year():
    assert not gc.widely_used({"a", "b"}, {21, 22})
    assert not gc.widely_used({"a", "b", "c"}, {21})
    assert gc.widely_used({"a", "b", "c"}, {21, 22})
    assert gc.widely_used({str(i) for i in range(6)}, {21})


def test_only_reused_wording_is_offered_and_never_the_firm():
    rows = _rows(_reports())
    texts = "\n".join(r["text"] for r in rows)
    assert "notice of claim" in texts and "precise stage of damage" in texts and "Light test" in texts
    # one importer's project: five cases, but all in one year
    assert "tarpaulin" not in texts
    # the firm's name and its letterhead
    assert FIRM.lower() not in texts.lower() and "offices in" not in texts.lower()
    # a loading survey is a different job
    assert "lashing" not in texts
    # the other report's date is a blank
    assert "3 March" not in texts and "[DATE]" in texts


def test_cards_in_order():
    rows = _rows(_reports())
    app_cards = gc.offer(rows, form_section="application", mode="SEA")
    assert [c["topic"] for c in app_cards] == ["asked", "notice"]
    survey = gc.offer(rows, form_section="survey_findings", mode="SEA")
    card = next(c for c in survey if c["topic"] == "container")
    assert "externally sound" in card["text"] and "Light test" in card["text"]
    # AIR report: sea wording is offered only when it says nothing about sea or air
    air = gc.offer(rows, form_section="survey_findings", mode="AIR")
    assert all("container" not in c["text"].lower() for c in air)


def test_a_card_holds_choices_and_extras_and_no_section_has_more_than_five():
    rows = _rows(_reports())
    for sec in ("application", "circumstances_of_loss", "survey_findings", "cause_of_loss", "next_step", "documentation"):
        assert len([c for c in gc.offer(rows, form_section=sec, mode="SEA") if not c["compact"]]) <= 5
    card = next(c for c in gc.offer(rows, form_section="survey_findings", mode="SEA") if c["topic"] == "container")
    # the default text is the pieces that are on, in order
    on = [p["choices"][0]["text"] for p in card["parts"] if p["on"]]
    assert card["text"] == "\n\n".join(on)
    assert any(p["optional"] for p in card["parts"])


def test_an_idea_worded_differently_each_time_becomes_one_sentence_with_this_reports_facts():
    rows = _rows(_reports())
    values = {"vessel": "MSC TEST", "voyage": "123W", "port_of_discharge": "Nhava Sheva Port",
              "date_of_arrival": "2 June 2026", "container_nos": ["TSTU1234565"]}
    card = next(c for c in gc.offer(rows, form_section="circumstances_of_loss", mode="SEA", values=values)
                if c["topic"] == "arrival")
    t = card["text"]
    assert "MSC TEST" in t and "123W" in t and "Nhava Sheva Port" in t and "2 June 2026" in t and "TSTU1234565" in t
    # nothing of the reports it came from: vessels, containers, sizes, CFS names
    for other in ("Sea Star", "Blue Moon", "Red Sun", "ABCU", "40’HC", "Alpha", "Beta", "Gamma"):
        assert other not in t
    # what the report does not know stays a visible blank
    assert card["blanks"] == ["[CFS]"]


def test_cargo_and_loss_specific_wording_only_where_it_fits():
    rows = _rows(_reports())

    def texts(**kw):
        return "\n".join(c["text"] for c in gc.offer(rows, form_section="survey_findings", mode="SEA", **kw))

    # names bags: only for a bagged cargo
    assert "remaining bags" not in texts()
    assert "remaining bags" in texts(cargo_type="BAGGED_FOOD")
    assert "remaining bags" not in texts(cargo_type="STEEL_METALS")
    # names bags and water: bagged cargo, and only when the loss is wet
    assert "silver nitrate" not in texts(cargo_type="BAGGED_FOOD")
    assert "silver nitrate" in texts(cargo_type="BAGGED_FOOD", loss_types=["wet"])
    # the light test is not a leak
    assert gc.losses_named("Light test: no leakage / penetration of light was noted.") == []


def test_a_final_report_does_not_say_a_final_report_will_follow():
    rows = _rows(_reports())
    final = "\n".join(c["text"] for c in gc.offer(rows, form_section="next_step", mode="SEA"))
    prelim = "\n".join(c["text"] for c in gc.offer(rows, form_section="next_step", mode="SEA", state="PRELIMINARY"))
    assert "final report will be issued" not in final
    assert "final report will be issued" in prelim


@pytest.mark.asyncio
async def test_pick_endpoint_gives_general_cargo_its_own_wording(monkeypatch):
    rows = _rows(_reports())

    async def fake_load(db):
        return rows

    monkeypatch.setattr(gc, "load_library", fake_load)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        login = await ac.post("/api/auth/login", json={"password": "surveyor123"})
        hdr = {"Authorization": f"Bearer {login.json()['token']}"}
        res = await ac.post("/api/clauses/pick", json={"section": "cause_of_loss", "commodity": "GENERAL_CARGO",
                                                       "mode": "SEA"}, headers=hdr)
        assert res.status_code == 200
        assert [t["topic"] for t in res.json()["topics"]] == ["stage"]
        res = await ac.post("/api/clauses/pick", json={"section": "note", "commodity": "GENERAL_CARGO"}, headers=hdr)
        assert res.json()["topics"] == []


CORPUS = Path(os.environ.get("CORPUS_DIR", "D:/marine-corpus"))


@pytest.mark.skipif(not gc.corpus_file(CORPUS).exists(), reason="the report archive is not on this machine")
def test_nothing_from_the_real_archive_names_the_firm_or_its_files():
    rows = gc.build_topic_texts(gc.load_reports(CORPUS))
    assert rows
    for r in rows:
        assert not gc.foreign(r.text), r.text
        assert not gc._LETTERHEAD.search(r.text), r.text
        assert "preliminary" not in r.text.lower(), r.text
