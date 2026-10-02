"""
The surveyor's notes written up by Gemini: never trusted for facts, and the
report never depends on it. No real call is made here.
"""

import pytest

from app.config import settings
from app.ingest.tally import cloud_reader
from app.services import notes_writer as nw

NOTES = "45 bags wet at bottom tier, container TSTU1234565 seal intact, CHA Mr. Shah present"
VALUES = {"survey_date": "5 June 2026", "container_nos": ["TSTU1234565"]}
EXAMPLES = ["Upon checking the same, the details noted are as follows:",
            "The remaining [COUNT] [PACKAGES] were found in an apparently sound condition."]


def test_what_the_notes_and_facts_say_passes():
    text = ("On 5 June 2026, we found that 45 bags stowed at the bottom tier of Container No. TSTU1234565 were wet. "
            "The seal was found intact. Mr. Shah of the consignees' CHA attended the survey.")
    assert nw.check_facts(text, NOTES, VALUES, EXAMPLES) == []


def test_a_figure_a_container_or_a_name_it_was_not_given_is_flagged():
    text = ("We found 60 bags wet in Container No. ABCU7654321. Mr. Kumar of Alpha Logistics attended. "
            "The cause appears to be [NUMBER] days of rain.")
    flagged = nw.check_facts(text, NOTES, VALUES, EXAMPLES)
    assert "60" in flagged and "ABCU7654321" in flagged and "Kumar" in flagged and "Alpha" in flagged
    # a blank is not a fact
    assert not any("NUMBER" in f for f in flagged)
    assert nw.check_facts("As per Gladstone file G/1234/21B.", NOTES, VALUES, EXAMPLES)[0] == "another firm's name or file number"


def test_a_sentence_the_notes_do_not_back_is_left_out():
    notes = "container opened in our presence, 45 bags wet at bottom tier, seal intact, floor wet near door"
    text = ("Upon checking the same, the details noted are as follows:\n\n"
            "• The container was found in an externally sound condition except for normal wear and tear.\n"
            "• The container's side wall and door panels were found in an apparently sound condition.\n"
            "• The floor was found wet near the door.\n"
            "• 45 bags were found wet at the bottom tier.")
    kept, removed = nw.split_supported(text, notes, {})
    assert "floor was found wet" in kept and "45 bags" in kept and kept.startswith("Upon checking")
    assert len(removed) == 2 and all("sound condition" in s for s in removed)
    # "Mr." does not end the sentence
    kept, removed = nw.split_supported("The consignees' custom house agent Mr. Shah attended the survey.",
                                       "CHA Mr. Shah attended", {})
    assert kept == "The consignees' custom house agent Mr. Shah attended the survey." and removed == []


@pytest.mark.asyncio
async def test_no_key_keeps_the_notes_as_typed(monkeypatch):
    monkeypatch.setattr(settings, "GEMINI_API_KEY", "")
    d = await nw.write_up("survey_findings", NOTES, VALUES, EXAMPLES)
    assert d.text == NOTES and d.source == "notes" and "not set up" in d.message


@pytest.mark.asyncio
async def test_no_model_answering_keeps_the_notes_as_typed(monkeypatch):
    monkeypatch.setattr(settings, "GEMINI_API_KEY", "test-key")

    async def busy(body):
        return None, None, "Today's free reading allowance is used up."

    monkeypatch.setattr(cloud_reader, "_race_models", busy)
    d = await nw.write_up("survey_findings", NOTES, VALUES, EXAMPLES)
    assert d.text == NOTES and d.source == "notes" and "allowance" in d.message


@pytest.mark.asyncio
async def test_an_answer_is_returned_with_what_to_check(monkeypatch):
    monkeypatch.setattr(settings, "GEMINI_API_KEY", "test-key")
    sent = {}

    async def answer(body):
        sent["prompt"] = body["contents"][0]["parts"][0]["text"]
        return {"text": "We found 45 bags wet at the bottom tier.\n\n\n\n• 12 bags were torn."}, "model-x", None

    monkeypatch.setattr(cloud_reader, "_race_models", answer)
    d = await nw.write_up("survey_findings", NOTES, VALUES, EXAMPLES)
    assert d.source == "gemini:model-x"
    assert "\n\n\n" not in d.text
    assert d.flagged == ["12"]
    # only the notes, the report's facts and the style sentences are sent
    assert NOTES in sent["prompt"] and "TSTU1234565" in sent["prompt"] and EXAMPLES[0] in sent["prompt"]
