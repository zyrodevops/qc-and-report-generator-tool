"""
The fruit picked on the New Report screen is the fruit the report is made for.

The screen lists fruits as FRUIT_CONFIG spells them (GRAPES, MANDARINS) and the
report builder spelt them singular. Every grapes report made from the screen
was quietly created as a Mandarin report, counted in pieces, so a grapes tally
weighed in kg came out as a sheet of unreadable cells.
"""

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.seeds.defaults import UnknownCommodity, fruit_key, get_default_block_state
from app.seeds.fruit_config import FRUIT_CONFIG

TEMPLATE = "perishable_sea_survey"


@pytest.mark.parametrize("picked", sorted(FRUIT_CONFIG))
def test_every_fruit_on_the_screen_builds_its_own_report(picked):
    state = get_default_block_state(TEMPLATE, commodity_key=picked)
    table = next(b for b in state["blocks"] if b["type"] == "table")
    assert state["metadata"]["commodity"] == fruit_key(picked)
    assert table["unit"] == FRUIT_CONFIG[picked]["unit"]


def test_grapes_is_not_turned_into_mandarin():
    state = get_default_block_state(TEMPLATE, commodity_key="GRAPES")
    table = next(b for b in state["blocks"] if b["type"] == "table")
    assert state["metadata"]["commodity"] == "GRAPE"
    assert "MANDARIN" not in state["report_title"]
    assert table["unit"] == "kg"
    assert "russet" not in [c["key"] for c in table["categories"]]


@pytest.mark.parametrize("bad", ["BANANA", "", None])
def test_unknown_or_missing_fruit_is_refused_not_guessed(bad):
    with pytest.raises(UnknownCommodity):
        get_default_block_state(TEMPLATE, commodity_key=bad)


@pytest.mark.asyncio
async def test_api_refuses_unknown_fruit_with_a_message():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        res = await ac.post("/api/auth/login", json={"password": "surveyor123"})
        hdr = {"Authorization": f"Bearer {res.json()['token']}"}
        res = await ac.post(
            "/api/reports",
            json={"family": "SURVEY_REPORT", "commodity": "BANANA", "template_id": TEMPLATE},
            headers=hdr,
        )
        assert res.status_code == 400
        assert "BANANA" in res.json()["detail"]


def test_paragraph_2_circumstances_for_apple_pear_mandarin_and_other_fruits():
    # Apple
    apple_state = get_default_block_state(TEMPLATE, commodity_key="APPLE")
    apple_para2 = next(b for b in apple_state["blocks"] if b.get("id") == "b_para2")
    apple_note = next(b for b in apple_state["blocks"] if b.get("id") == "b_note")
    assert "We were apprised that subsequent to its discharge" in apple_para2["additional_text"]
    assert "Apple fruits had sustained damage" in apple_para2["additional_text"]
    assert apple_note["additional_text"] == ""

    # Pear
    pear_state = get_default_block_state(TEMPLATE, commodity_key="PEAR")
    pear_para2 = next(b for b in pear_state["blocks"] if b.get("id") == "b_para2")
    pear_note = next(b for b in pear_state["blocks"] if b.get("id") == "b_note")
    assert "We were apprised that subsequent to its discharge" in pear_para2["additional_text"]
    assert "Pear fruits had sustained damage" in pear_para2["additional_text"]
    assert pear_note["additional_text"] == ""

    # Mandarin
    mandarin_state = get_default_block_state(TEMPLATE, commodity_key="MANDARINS")
    mandarin_para2 = next(b for b in mandarin_state["blocks"] if b.get("id") == "b_para2")
    mandarin_note = next(b for b in mandarin_state["blocks"] if b.get("id") == "b_note")
    assert "It was reported to us that after landing from the vessel" in mandarin_para2["additional_text"]
    assert "[Vessel Name & Voyage No.]" in mandarin_para2["additional_text"]
    assert "[Port of Discharge]" in mandarin_para2["additional_text"]
    assert "[Discharge Date]" in mandarin_para2["additional_text"]
    assert "[Container No.]" in mandarin_para2["additional_text"]
    assert "mandarin fruits in a damaged condition" in mandarin_para2["additional_text"]
    assert "Upon our arrival, we noted that the container was no longer available on site" in mandarin_note["additional_text"]

    # Grapes
    grapes_state = get_default_block_state(TEMPLATE, commodity_key="GRAPES")
    grapes_para2 = next(b for b in grapes_state["blocks"] if b.get("id") == "b_para2")
    grapes_note = next(b for b in grapes_state["blocks"] if b.get("id") == "b_note")
    assert "It was reported to us that after discharge from the carrying vessel" in grapes_para2["additional_text"]
    assert "drayed by truck and received at the inland depot / CFS" in grapes_para2["additional_text"]
    assert "fresh grape fruits in a damaged condition" in grapes_para2["additional_text"]
    assert "[Delivery Date]" in grapes_para2["additional_text"]
    assert grapes_note["additional_text"] == ""

    # Plum
    plum_state = get_default_block_state(TEMPLATE, commodity_key="PLUM")
    plum_para2 = next(b for b in plum_state["blocks"] if b.get("id") == "b_para2")
    plum_note = next(b for b in plum_state["blocks"] if b.get("id") == "b_note")
    assert "It was reported that following discharge from the vessel" in plum_para2["additional_text"]
    assert "1x40’ High Cube refrigerated container" in plum_para2["additional_text"]
    assert "fresh plums in a severely deteriorated condition" in plum_para2["additional_text"]
    assert "conduct a survey to ascertain the nature, extent, and cause of the reported damage" in plum_para2["additional_text"]
    assert "joint survey in the presence of surveyors" not in plum_para2["additional_text"]
    assert "[Delivery Date]" in plum_para2["additional_text"]
    assert plum_note["additional_text"] == ""

    # Other fruits (Orange, Kiwi, Avocado) must remain empty
    for other in ["ORANGE", "KIWI", "AVOCADO"]:
        other_state = get_default_block_state(TEMPLATE, commodity_key=other)
        other_para2 = next(b for b in other_state["blocks"] if b.get("id") == "b_para2")
        other_note = next(b for b in other_state["blocks"] if b.get("id") == "b_note")
        assert other_para2["additional_text"] == "", f"Expected empty para2 for {other}"
        assert other_note["additional_text"] == "", f"Expected empty note for {other}"


def test_paragraph_2_1_our_survey_templates_and_measurements_inclusion():
    """
    Paragraph 2.1 (Our Survey) must be pre-populated for Apple, Pear, Mandarin, Grapes, and Plum,
    and b_measurements.included must be False so the redundant standalone table does not render in preview/DOCX.
    Other fruits must remain empty for Paragraph 2.1 and have b_measurements.included as True.
    """
    # Apple
    apple_state = get_default_block_state(TEMPLATE, commodity_key="APPLE")
    apple_p21 = next(b for b in apple_state["blocks"] if b.get("id") == "b_para2_1")
    apple_meas = next(b for b in apple_state["blocks"] if b.get("id") == "b_measurements")
    assert "THE CONDITION FOUND OF APPLE FRUITS:" in apple_p21["additional_text"]
    assert "pulp temperature of the Apple fruits was measured" in apple_p21["additional_text"]
    assert "measured using a penetrometer" in apple_p21["additional_text"]
    assert apple_meas.get("included") is False

    # Pear
    pear_state = get_default_block_state(TEMPLATE, commodity_key="PEAR")
    pear_p21 = next(b for b in pear_state["blocks"] if b.get("id") == "b_para2_1")
    pear_meas = next(b for b in pear_state["blocks"] if b.get("id") == "b_measurements")
    assert "THE CONDITION FOUND OF PEAR FRUITS:" in pear_p21["additional_text"]
    assert "pulp temperature of the Pear fruits was measured" in pear_p21["additional_text"]
    assert "measured using a penetrometer" in pear_p21["additional_text"]
    assert pear_meas.get("included") is False

    # Mandarin
    mandarin_state = get_default_block_state(TEMPLATE, commodity_key="MANDARIN")
    mandarin_p21 = next(b for b in mandarin_state["blocks"] if b.get("id") == "b_para2_1")
    mandarin_meas = next(b for b in mandarin_state["blocks"] if b.get("id") == "b_measurements")
    assert "fresh mandarin fruits was checked by means of a digital thermometer" in mandarin_p21["additional_text"]
    assert "Upon cutting the mandarin fruits, the pulp was found juicy." in mandarin_p21["additional_text"]
    assert "penetrometer" not in mandarin_p21["additional_text"]
    assert mandarin_meas.get("included") is False

    # Grapes
    grapes_state = get_default_block_state(TEMPLATE, commodity_key="GRAPES")
    grapes_p21 = next(b for b in grapes_state["blocks"] if b.get("id") == "b_para2_1")
    grapes_meas = next(b for b in grapes_state["blocks"] if b.get("id") == "b_measurements")
    assert "pulp temperature of the grapes was checked" in grapes_p21["additional_text"]
    assert "Grape’s berries size was checked using a vernier caliper" in grapes_p21["additional_text"]
    assert "penetrometer" not in grapes_p21["additional_text"]
    assert grapes_meas.get("included") is False

    # Plum
    plum_state = get_default_block_state(TEMPLATE, commodity_key="PLUM")
    plum_p21 = next(b for b in plum_state["blocks"] if b.get("id") == "b_para2_1")
    plum_meas = next(b for b in plum_state["blocks"] if b.get("id") == "b_measurements")
    assert "Reefer operational parameters registered a set point" in plum_p21["additional_text"]
    assert "Cross-sectional cutting of representative fruit specimens revealed internal breakdown" in plum_p21["additional_text"]
    assert plum_meas.get("included") is False

    # Other fruits
    for other in ["ORANGE", "KIWI", "AVOCADO"]:
        other_state = get_default_block_state(TEMPLATE, commodity_key=other)
        other_p21 = next(b for b in other_state["blocks"] if b.get("id") == "b_para2_1")
        other_meas = next(b for b in other_state["blocks"] if b.get("id") == "b_measurements")
        assert other_p21["additional_text"] == "", f"Expected empty para2_1 for {other}"
        assert other_meas.get("included") is True, f"Expected included=True for {other}"


def test_paragraph_4_next_step_defaults():
    # Apple & Pear use the 2-sentence version with claims direction (M-161 to M-164)
    for fruit in ["APPLE", "PEAR"]:
        state = get_default_block_state(TEMPLATE, commodity_key=fruit)
        p4 = next(b for b in state["blocks"] if b.get("id") == "b_next_step")
        assert "sell them immediately" in p4["additional_text"]
        assert "directly with the responsible parties" in p4["additional_text"]
        assert fruit.capitalize() in p4["additional_text"]

    # Grapes, Mandarin, Plum use the single-sentence version (M-167, M-168)
    for fruit in ["GRAPES", "MANDARIN", "PLUM"]:
        state = get_default_block_state(TEMPLATE, commodity_key=fruit)
        p4 = next(b for b in state["blocks"] if b.get("id") == "b_next_step")
        assert "As an act to mitigate the loss" in p4["additional_text"]
        assert "as soon as possible to avoid further damages" in p4["additional_text"]
        assert fruit.lower() in p4["additional_text"].lower()


def test_paragraph_5_documentation_defaults():
    for fruit in ["APPLE", "PEAR", "GRAPES", "MANDARIN", "PLUM"]:
        state = get_default_block_state(TEMPLATE, commodity_key=fruit)
        p5 = next(b for b in state["blocks"] if b.get("id") == "b_doc")
        assert "Documentation secured during our initial inquiries" in p5["additional_text"]
        assert "Bill of Lading" in p5["additional_text"]
        assert "Packing List" in p5["additional_text"]
        assert "survey photographs were taken during the inspection" in p5["additional_text"]
        assert "Dropbox link" in p5["additional_text"]




