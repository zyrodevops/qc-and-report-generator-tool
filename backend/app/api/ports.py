"""
Ports API — provides port normalization, country resolution, and voyage formatting.
"""

from typing import Optional
from fastapi import APIRouter
from pydantic import BaseModel

from app.utils.port_normalizer import (
    normalize_port_name,
    normalize_voyage,
    has_country,
    get_port_country,
)

router = APIRouter()


class NormalizeVoyageRequest(BaseModel):
    voyage: str
    port: Optional[str] = None


class NormalizeVoyageResponse(BaseModel):
    original_voyage: str
    normalized_voyage: str
    normalized_port: Optional[str] = None
    country: Optional[str] = None


@router.post("/ports/normalize", response_model=NormalizeVoyageResponse)
def normalize_voyage_endpoint(payload: NormalizeVoyageRequest):
    """
    Normalizes a voyage string (e.g. 'Navegantes, SC, Brazil to Nhava Sheva')
    or individual port name, appending country if missing.
    """
    normalized_v = normalize_voyage(payload.voyage, fetch_online=True)
    norm_port = normalize_port_name(payload.port, fetch_online=True) if payload.port else None
    country = get_port_country(payload.port or payload.voyage, fetch_online=True)

    return NormalizeVoyageResponse(
        original_voyage=payload.voyage,
        normalized_voyage=normalized_v,
        normalized_port=norm_port,
        country=country,
    )
