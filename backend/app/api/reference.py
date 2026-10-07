"""
The client's private lists for the report form, for logged-in users only.

They used to be JSON files built into the frontend, so anyone who opened the
site could read every name in them. See app.seeds.private_data.
"""

import hashlib

from fastapi import APIRouter, Depends, HTTPException, Request, Response

from app.config import settings
from app.core.auth import UserSession, get_current_user
from app.seeds.private_data import banner_jpeg, load_cold_storages, load_staff

router = APIRouter()


@router.get("/reference-data")
def reference_data(current_user: UserSession = Depends(get_current_user)):
    """Staff and surveyors (attendance table), cold storages (Paragraph 1), and
    the surveyor licence number printed in the closing of a survey report."""
    return {
        "staff": load_staff(),
        "cold_storages": load_cold_storages(),
        "licence_no": settings.IRDAI_LICENCE_NUMBER or "",
        "has_banner": banner_jpeg() is not None,
    }


@router.get("/reference-data/banner.jpg")
def banner(request: Request, current_user: UserSession = Depends(get_current_user)):
    """The page 1 banner, for the A4 preview. The browser re-checks it on each
    load (a cheap 304 when unchanged), so a new banner file shows at once."""
    data = banner_jpeg()
    if data is None:
        raise HTTPException(status_code=404, detail="No banner on this server.")
    etag = '"' + hashlib.sha1(data).hexdigest()[:20] + '"'
    headers = {"Cache-Control": "private, no-cache", "ETag": etag}
    if request.headers.get("if-none-match") == etag:
        return Response(status_code=304, headers=headers)
    return Response(content=data, media_type="image/jpeg", headers=headers)
