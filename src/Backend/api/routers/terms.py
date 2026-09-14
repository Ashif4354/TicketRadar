# src/Backend/api/routers/terms.py

import logging
from fastapi import APIRouter, HTTPException, Depends

from lib.core.auth import get_authorized_user
from lib.services.terms import TermsService
from api.schemas import AcceptTermsRequest

logger = logging.getLogger("ticketradar.api.terms")

router = APIRouter(prefix="/api/terms", tags=["Terms"])

@router.get("/status")
async def get_terms_status(claims: dict = Depends(get_authorized_user)):
    """Returns whether the current user has accepted the latest terms version."""
    uid = claims.get("uid")
    if not uid:
        raise HTTPException(status_code=401, detail="User identification missing.")

    current_ver = TermsService.get_current_version()
    accepted = TermsService.check_terms_accepted(uid)
    return {
        "uid": uid,
        "current_version": current_ver,
        "accepted": accepted,
    }

@router.post("/accept")
async def accept_terms(
    payload: AcceptTermsRequest,
    claims: dict = Depends(get_authorized_user)
):
    """Records the user's acceptance of the specified terms version."""
    uid = claims.get("uid")
    if not uid:
        raise HTTPException(status_code=401, detail="User identification missing.")

    success = TermsService.accept_terms(uid, payload.version)
    if not success:
        raise HTTPException(status_code=500, detail="Failed to record terms acceptance.")

    return {
        "success": True,
        "version": payload.version,
        "message": f"Terms version {payload.version} accepted successfully."
    }
