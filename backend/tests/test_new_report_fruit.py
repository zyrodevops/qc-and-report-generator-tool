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
