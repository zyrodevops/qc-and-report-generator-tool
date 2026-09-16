import pytest
from fastapi.testclient import TestClient
from backend.app.main import app

client = TestClient(app)


def test_clause_taxonomy_causes_apple():
    res = client.get("/api/clause-taxonomy?section=cause_of_loss&commodity=APPLE")
    assert res.status_code == 200
    data = res.json()
    assert data["section"] == "cause_of_loss"
    assert len(data["causes"]) == 6
    apple_temp = next(c for c in data["causes"] if c["key"] == "TEMPERATURE_EXCURSION")
    assert "Apple" in apple_temp["wording"]
    assert apple_temp["is_commodity_specific"] is True


def test_clause_taxonomy_next_step():
    res = client.get("/api/clause-taxonomy?section=next_step&commodity=GRAPE")
    assert res.status_code == 200
    data = res.json()
    assert data["section"] == "next_step"
    assert len(data["actions"]) >= 5
    sell_action = next(a for a in data["actions"] if a["key"] == "SELL_IMMEDIATELY")
    assert sell_action["is_applicable"] is True
    assert "Grape" in sell_action["text"]


def test_clause_taxonomy_circumstances_scenarios():
    res = client.get("/api/clause-taxonomy?section=circumstances_of_loss&commodity=APPLE")
    assert res.status_code == 200
    data = res.json()
    assert data["section"] == "circumstances_of_loss"
    assert len(data["scenarios"]) >= 3
    labels = [s["label"] for s in data["scenarios"]]
    assert any("Sea Transit" in l for l in labels)
    assert any("Detention" in l for l in labels)
    for s in data["scenarios"]:
        assert "Apple" in s["template"]


def test_clause_taxonomy_note_scenarios():
    res = client.get("/api/clause-taxonomy?section=note&commodity=ORANGE")
    assert res.status_code == 200
    data = res.json()
    assert data["section"] == "note"
    assert len(data["scenarios"]) >= 2
    for s in data["scenarios"]:
        assert "NOTE:" in s["template"]
