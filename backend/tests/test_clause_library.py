"""
Standard wording: the client's own, as topics, with the source report's
facts blanked.

Every sentence here is made up for the test. The client's reports are not in
the repository and must not be copied into it.
"""

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.seeds.clause_library import (
    bind,
    blanks_in,
    build_topic_texts,
    csv_fruit_key,
    offer,
    to_template,
)
from app.seeds.defaults import get_default_block_state

VOCAB = {"from", "different", "locations", "cold", "storage", "the", "were"}


# ---------------------------------------------------------------------------
# Another report's facts become blanks
# ---------------------------------------------------------------------------

def test_names_counts_and_photo_numbers_are_blanked():
    t = to_template(
        "The consignee's representative, Mr. Ravi Kumar, presented 1,176 boxes across 4 counts. "
        "(Photo Nos. 1 to 6)", VOCAB,
    )
    assert "Ravi" not in t and "Kumar" not in t and "1,176" not in t
    assert "[NAME]" in t and "[NUMBER] boxes" in t and "(Photo Nos. [NUMBERS])" in t


def test_dates_and_container_numbers_are_blanked():
    assert to_template("by their email dated 6 May 2026, requested", VOCAB) == "by their email dated [DATE], requested"
    assert "[DATE]" in to_template("attended on 12.08.2026 at site", VOCAB)
    assert to_template("TGHU1234567 carrying the subject cargo", VOCAB).startswith("[CONTAINER NO.]")


def test_a_bracketed_cold_store_and_address_becomes_one_blank():
    t = to_template("we attended the facility (Frosty Agro Cold Storage, Plot No. 12, Wagholi, Pune) on 3 May 2026", VOCAB)
    assert "([NAME])" in t
    assert "Frosty" not in t and "Wagholi" not in t and "Cold Storage" not in t


def test_ordinary_capitalised_words_and_degrees_survive():
    t = to_template("(Photo Nos. 5 & 6) From different locations the temperature was 0°C.", VOCAB)
    assert "From different locations" in t
    assert "[NUMBER]°C" in t


def test_all_caps_names_are_blanked_even_when_they_are_english_words():
    t = to_template("The container was carried by EVER and later ONE vessel.", {"ever", "one", "container", "was"})
    assert "EVER" not in t and "ONE" not in t


# ---------------------------------------------------------------------------
# Only what this report knows is filled in
# ---------------------------------------------------------------------------

def test_pulp_pressure_and_container_are_filled_from_the_report():
    tpl = to_template(
        "TGHU1234567 arrived. The pulp temperature was registered in the range of 0.3°C to 1.1°C. "
        "Pressure of the sound fruits was noted in the range of 5.87 LBS to 7.74 LBS.", VOCAB,
    )
    out = bind(tpl, {"container_no": "MSKU7654321", "pulp_min": "0.6", "pulp_max": "1",
                     "pressure_min": "16.88", "pressure_max": "17.59"})
    assert out.startswith("MSKU7654321 arrived.")
    assert "0.6°C to 1°C" in out
    assert "16.88 LBS to 17.59 LBS" in out
    assert "0.3" not in out and "5.87" not in out


def test_nothing_is_filled_when_the_report_does_not_have_it():
    tpl = to_template("The pulp temperature was registered in the range of 0.3°C to 1.1°C.", VOCAB)
    assert bind(tpl, {}) == tpl
    assert blanks_in(bind(tpl, {})) == ["[NUMBER]", "[NUMBER]"]
    # A placeholder in the report is not a value.
    assert "[Container No.]" not in bind("[CONTAINER NO.] was shifted", {"container_no": "[Container No.]"})


def test_pulp_values_do_not_go_into_the_set_point_sentence():
    tpl = to_template("As per the Bill of Lading, the requested temperature for this shipment was 0°C.", VOCAB)
    out = bind(tpl, {"pulp_min": "0.6", "pulp_max": "1"})
    assert "0.6" not in out and "[NUMBER]°C" in out


# ---------------------------------------------------------------------------
# Topics built from whole reports
# ---------------------------------------------------------------------------

def _report(fruit, cause, extra="", arrival="landing from the vessel “SEA STAR” Voy No. 527W at the port on 3 May 2026"):
    """A made-up report in the client's layout."""
    return {"fruit": fruit, "text": (
        "PARAGRAPH 1: SURVEY APPLICATION:\n \n"
        "At the Consignee's telephonic survey request and as per the appointment given, we visited "
        "the cold storage on 3 May 2026 to carry out an independent survey.\n \n"
        "PARAGRAPH 2: CIRCUMSTANCES OF LOSS:\n \n"
        f"It was reported to us that after {arrival}, the subject cargo was received.\n \n"
        "PARAGRAPH 3: CAUSE OF LOSS:\n \n"
        f"As per the Bill of Lading, the requested temperature for this shipment of fresh {fruit.lower()} "
        "fruits was 0°C.\n \n" + cause + "\n \n" + extra +
        "PARAGRAPH 4: NEXT STEP:\n \n"
        "To mitigate losses we advised the Consignees to sell the damaged cargo immediately.\n"
    )}


NO_DATA = "In the course of our investigation, we were not provided with the downloads of the temperature recorders."
FINE = ("In view of the above, no substantial variation in temperature was recorded during the entire sea "
        "transit, so the damage was due to pre-shipment reasons.")
FACTORS = ("Contributing factors observed for this cargo include:\n"
           "• \nMechanical injury likely from automated sorting\n"
           "• Pre-harvest issues such as russet marks\n \n")


def _rows(reports):
    return [dict(id=r.row_id, text=r.text, form_section=r.form_section, topic=r.topic, fruit=r.fruit, mode=r.mode,
                 rank=r.rank, reports=r.reports, position=r.position, fruits_named=r.fruits_named,
                 mode_neutral=r.mode_neutral)
            for r in build_topic_texts(reports)]


def _three(fruit, cause, extra="", **kw):
    return [_report(fruit, cause, extra, **kw) for _ in range(3)]


def test_fruit_keys_match_the_archive():
    assert csv_fruit_key("GRAPE") == "GRAPES" and csv_fruit_key("MANDARINS") == "MANDARINS"
    assert csv_fruit_key("STEEL_METALS") is None


def test_related_ideas_share_a_card_and_each_card_says_what_it_is():
    rows = _rows(_three("APPLE", NO_DATA, FACTORS) + _three("APPLE", FINE))
    topics = {c["topic"]: c for c in offer(rows, form_section="cause_of_loss", fruit="APPLE", values={})}
    assert {"requested", "no_data", "fine"} <= set(topics)
    assert topics["requested"]["text"] == "As per the Bill of Lading, the requested temperature for this shipment of fresh apple fruits was [NUMBER]°C."
    assert "not provided with the downloads" in topics["no_data"]["text"]
    assert "not provided" not in topics["fine"]["text"]
    assert "Contributing factors observed" in topics["fine"]["text"]


def test_bullets_stay_bullets():
    rows = _rows(_three("APPLE", FINE, FACTORS))
    text = next(c for c in offer(rows, form_section="cause_of_loss", fruit="APPLE", values={}) if c["topic"] == "fine")["text"]
    # "•" alone on its line with the text on the next is still one bullet.
    assert text.endswith("Contributing factors observed for this cargo include:\n\n"
                    "• Mechanical injury likely from automated sorting\n"
                    "• Pre-harvest issues such as russet marks")


def test_abbreviations_do_not_cut_a_sentence():
    rows = _rows(_three("APPLE", NO_DATA))
    arrival = next(c for c in offer(rows, form_section="circumstances_of_loss", fruit="APPLE", values={})
                   if c["topic"] == "arrival")["text"]
    assert "Voy No. [NUMBER] at the port on [DATE]" in arrival


def test_a_sentence_used_in_fewer_than_three_reports_is_never_offered():
    one_off = "The cargo was subjected to extreme heat exposure at the port on that particular day.\n \n"
    reports = [_report("APPLE", NO_DATA, one_off), _report("APPLE", NO_DATA, one_off), _report("APPLE", NO_DATA)]
    texts = " ".join(c["text"] for c in offer(_rows(reports), form_section="cause_of_loss", fruit="APPLE", values={}))
    assert "extreme heat" not in texts


def test_another_fruits_wording_is_not_offered_and_never_rewritten():
    rows = _rows(_three("APPLE", NO_DATA))
    grapes = offer(rows, form_section="cause_of_loss", fruit="GRAPES", values={})
    assert all("apple" not in c["text"].lower() for c in grapes)
    assert "requested" not in {c["topic"] for c in grapes}  # the apple sentence is not turned into grapes
    # Text that names no fruit is fine to share.
    assert [c["topic"] for c in offer(rows, form_section="next_step", fruit="GRAPES", values={})] == ["sell"]


def test_sea_and_air_come_from_the_report_type():
    sea = _three("APPLE", NO_DATA)
    air = _three("APPLE", NO_DATA, arrival="landing from Flight No. “EK 500” at the airport on 3 May 2026")
    rows = _rows(sea + air)
    by_sea = next(c for c in offer(rows, form_section="circumstances_of_loss", fruit="APPLE", mode="SEA", values={})
                  if c["topic"] == "arrival")["text"]
    by_air = next(c for c in offer(rows, form_section="circumstances_of_loss", fruit="APPLE", mode="AIR", values={})
                  if c["topic"] == "arrival")["text"]
    assert "vessel" in by_sea and "Flight" not in by_sea
    assert "Flight" in by_air and "vessel" not in by_air


def test_counted_defects_choose_the_wording_but_never_add_anything():
    plain = "Contributing factors observed for this cargo include:\n• Mechanical injury likely from automated sorting\n \n"
    rows = _rows(_three("APPLE", FINE, plain) + _three("APPLE", FINE, FACTORS))
    links = [{"fruit": "APPLE", "term": "russet", "rate": 89.0}]
    with_russet = offer(rows, form_section="cause_of_loss", fruit="APPLE", values={}, defects=["Russet"], links=links)
    without = offer(rows, form_section="cause_of_loss", fruit="APPLE", values={}, defects=[], links=links)
    contributing = next(c for c in with_russet if c["topic"] == "fine")
    assert "russet" in contributing["text"].lower()
    assert [c["topic"] for c in with_russet] == [c["topic"] for c in without]


def test_the_surveyor_is_not_shown_statistics():
    rows = _rows(_three("APPLE", NO_DATA))
    for c in offer(rows, form_section="application", fruit="APPLE", values={}):
        assert set(c) == {"topic", "label", "description", "compact", "text", "blanks"}


def test_attendee_rows_never_become_wording():
    attendees = "Mr. Ravi Kumar QC In-Charge Frosty Fresh Pvt Ltd (Consignees)\n \n"
    rows = _rows(_three("APPLE", NO_DATA, attendees))
    texts = " ".join(c["text"] for c in offer(rows, form_section="cause_of_loss", fruit="APPLE", values={}))
    assert "Ravi" not in texts and "Frosty" not in texts


def test_filling_values_keeps_the_layout():
    text = "The pulp temperature was found in the range of [NUMBER]°C to [NUMBER]°C.\n\n• First point\n• Second point"
    out = bind(text, {"pulp_min": "0.6", "pulp_max": "1"})
    assert out == "The pulp temperature was found in the range of 0.6°C to 1°C.\n\n• First point\n• Second point"


def test_a_per_count_pressure_line_is_not_given_the_overall_range():
    text = "The pressure was measured:\n\n• [VARIETY] ([NUMBER] Count): Range of [NUMBER] LBS to [NUMBER] LBS."
    out = bind(text, {"pressure_min": "14.18", "pressure_max": "17.59"})
    assert "14.18" not in out
    assert to_template("Red Delicious (100 Count): Range of 15 LBS to 17 LBS.").startswith("[VARIETY]")


# ---------------------------------------------------------------------------
# Printing: paragraphs and bullets
# ---------------------------------------------------------------------------

def test_paragraphs_and_bullets_print_as_such():
    from app.render.narrative_text import split_narrative
    from app.render.html.engine import render_narrative_html

    text = "One.\n\nFactors include:\n• Mechanical injury\n• Russet\n\nLast."
    assert split_narrative(text) == [("p", ["One."]), ("p", ["Factors include:"]),
                                     ("ul", ["Mechanical injury", "Russet"]), ("p", ["Last."])]
    html = render_narrative_html({"section": "CAUSE OF LOSS", "additional_text": text})
    assert "<ul><li>Mechanical injury</li><li>Russet</li></ul>" in html and html.count("<p>") == 3


# ---------------------------------------------------------------------------
# New reports and the API
# ---------------------------------------------------------------------------

def test_new_reports_start_with_blanks_not_guesses():
    state = get_default_block_state("perishable_sea_survey", commodity_key="APPLE")
    printed = str(state)
    for guess in ("Nhava Sheva", "JNPT", "Found Intact", "HC Reefer", "Mumbai Airport"):
        assert guess not in printed
    particulars = next(b for b in state["blocks"] if b["type"] == "particulars")
    assert {"label": "Port of Discharge", "value": ["[Port of Discharge]"]} in particulars["rows"]


def test_new_reports_start_with_empty_text_sections():
    state = get_default_block_state("perishable_sea_survey", commodity_key="APPLE")
    texts = [b["additional_text"] for b in state["blocks"] if b["type"] == "narrative"]
    assert texts and all(t == "" for t in texts)


@pytest.mark.asyncio
async def test_pick_endpoint_needs_a_login_and_skips_general_cargo():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        res = await ac.post("/api/clauses/pick", json={"section": "cause_of_loss", "commodity": "APPLE"})
        assert res.status_code == 401
        login = await ac.post("/api/auth/login", json={"password": "surveyor123"})
        hdr = {"Authorization": f"Bearer {login.json()['token']}"}
        res = await ac.post("/api/clauses/pick", json={"section": "cause_of_loss", "commodity": "APPLE", "mode": "SEA"}, headers=hdr)
        assert res.status_code == 200
        assert set(res.json()) >= {"topics", "available"}
        res = await ac.post("/api/clauses/pick", json={"section": "cause_of_loss", "commodity": "STEEL_METALS"}, headers=hdr)
        assert res.json()["topics"] == []


def test_the_busy_sections_have_a_few_cards_each():
    rows = _rows(_three("APPLE", NO_DATA, FACTORS) + _three("APPLE", FINE, FACTORS))
    for section, most in (("circumstances_of_loss", 4), ("survey_findings", 5), ("cause_of_loss", 5)):
        assert len(offer(rows, form_section=section, fruit="APPLE", values={})) <= most
