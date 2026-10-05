import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.utils.port_normalizer import (
    has_country,
    normalize_port_name,
    normalize_voyage,
    get_port_country,
)


def test_has_country_detection():
    assert has_country("Navegantes, SC, Brazil") is True
    assert has_country("Cape Town, South Africa") is True
    assert has_country("Dalian, China") is True
    assert has_country("Nhava Sheva, India") is True
    assert has_country("Nhava Sheva") is False
    assert has_country("Mundra") is False
    assert has_country("Valparaiso") is False
    assert has_country("[Port of Loading]") is True
    assert has_country("") is True


def test_normalize_port_name():
    assert normalize_port_name("Nhava Sheva", fetch_online=False) == "Nhava Sheva, India"
    assert normalize_port_name("Mundra", fetch_online=False) == "Mundra, India"
    assert normalize_port_name("Pipavav", fetch_online=False) == "Pipavav, India"
    assert normalize_port_name("Dalian", fetch_online=False) == "Dalian, China"
    assert normalize_port_name("Navegantes", fetch_online=False) == "Navegantes, Brazil"
    assert normalize_port_name("Cape Town, South Africa", fetch_online=False) == "Cape Town, South Africa"
    assert normalize_port_name("Navegantes, SC, Brazil", fetch_online=False) == "Navegantes, SC, Brazil"
    assert normalize_port_name("[Port of Discharge]", fetch_online=False) == "[Port of Discharge]"


def test_normalize_voyage():
    assert (
        normalize_voyage("Navegantes, SC, Brazil to Nhava Sheva", fetch_online=False)
        == "Navegantes, SC, Brazil to Nhava Sheva, India"
    )
    assert (
        normalize_voyage("Navegantes to Nhava Sheva", fetch_online=False)
        == "Navegantes, Brazil to Nhava Sheva, India"
    )
    assert (
        normalize_voyage("Valparaiso, Chile to Mundra", fetch_online=False)
        == "Valparaiso, Chile to Mundra, India"
    )
    assert (
        normalize_voyage("Cape Town, South Africa to Nhava Sheva, India", fetch_online=False)
        == "Cape Town, South Africa to Nhava Sheva, India"
    )
    assert (
        normalize_voyage("[Port of Loading] to [Port of Discharge]", fetch_online=False)
        == "[Port of Loading] to [Port of Discharge]"
    )


def test_ports_api_endpoint():
    client = TestClient(app)
    res = client.post(
        "/api/ports/normalize",
        json={"voyage": "Navegantes, SC, Brazil to Nhava Sheva"},
    )
    assert res.status_code == 200
    data = res.json()
    assert data["normalized_voyage"] == "Navegantes, SC, Brazil to Nhava Sheva, India"
    assert data["country"] == "India"
