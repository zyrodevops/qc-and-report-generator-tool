"""
The client's private lists for the report form, for logged-in users only.

They used to be JSON files built into the frontend, so anyone who opened the
site could read every name in them. See app.seeds.private_data.
"""

from fastapi import APIRouter, Depends

from app.core.auth import UserSession, get_current_user
from app.seeds.private_data import load_cold_storages, load_staff

router = APIRouter()


@router.get("/reference-data")
def reference_data(current_user: UserSession = Depends(get_current_user)):
    """Staff and surveyors (attendance table) and cold storages (Paragraph 1)."""
    return {"staff": load_staff(), "cold_storages": load_cold_storages()}
