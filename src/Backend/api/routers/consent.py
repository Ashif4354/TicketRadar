# src/Backend/api/routers/consent.py

import logging
from fastapi import APIRouter, HTTPException, Depends, Request
from google.cloud import firestore

from lib.core.auth import get_authorized_user, db
from lib.utils.phone import normalize_indian_phone
from api.schemas import OptInRequest

logger = logging.getLogger("ticketradar.api.consent")

router = APIRouter(prefix="/api/consent", tags=["Consent"])

@router.post("/{medium}/opt-in")
async def opt_in_medium(
    medium: str,
    request: Request,
    payload: OptInRequest = None,
    claims: dict = Depends(get_authorized_user)
):
    """Records explicit consent for a regulated notification channel (WhatsApp, SMS, Call)."""
    uid = claims.get("uid")
    medium_clean = medium.strip().lower().replace(" ", "_")
    if medium_clean not in ("whatsapp", "sms", "phone_call", "call"):
        raise HTTPException(status_code=400, detail=f"Unsupported consent medium: {medium}")

    consent_key = "call" if medium_clean in ("call", "phone_call") else medium_clean
    pref_key = "phone_call" if medium_clean in ("call", "phone_call") else medium_clean
    client_ip = request.client.host if request.client else ""

    update_data = {
        "uid": uid,
        f"{consent_key}_consented": True,
        f"{consent_key}_consented_at": firestore.SERVER_TIMESTAMP,
        f"{pref_key}_consented": True,
        "consent_source_ip": client_ip,
        "updated_at": firestore.SERVER_TIMESTAMP,
    }

    phone_e164 = None
    if payload and payload.phone_number:
        try:
            phone_e164 = normalize_indian_phone(payload.phone_number)
            update_data["phone_number"] = phone_e164
        except ValueError as ve:
            raise HTTPException(status_code=400, detail=str(ve))

    if db:
        db.collection("notification_consents").document(uid).set(update_data, merge=True)
        # Enable channel in preferences
        pref_update = {
            f"{pref_key}_enabled": True,
            "updated_at": firestore.SERVER_TIMESTAMP,
        }
        if phone_e164:
            if pref_key == "phone_call":
                pref_update["call_phone"] = phone_e164
            elif pref_key == "whatsapp":
                pref_update["whatsapp_phone"] = phone_e164
            elif pref_key == "sms":
                pref_update["sms_phone"] = phone_e164
        db.collection("notification_preferences").document(uid).set(pref_update, merge=True)

    logger.info(f"User {uid} opted in to {pref_key}.")
    return {"success": True, "message": f"Successfully opted in to {pref_key} alerts."}

@router.post("/{medium}/opt-out")
async def opt_out_medium(
    medium: str,
    claims: dict = Depends(get_authorized_user)
):
    """Revokes consent for a notification channel."""
    uid = claims.get("uid")
    medium_clean = medium.strip().lower().replace(" ", "_")
    if medium_clean not in ("whatsapp", "sms", "phone_call", "call"):
        raise HTTPException(status_code=400, detail=f"Unsupported consent medium: {medium}")

    consent_key = "call" if medium_clean in ("call", "phone_call") else medium_clean
    pref_key = "phone_call" if medium_clean in ("call", "phone_call") else medium_clean

    update_data = {
        "uid": uid,
        f"{consent_key}_consented": False,
        f"{consent_key}_revoked_at": firestore.SERVER_TIMESTAMP,
        f"{pref_key}_consented": False,
        "updated_at": firestore.SERVER_TIMESTAMP,
    }

    if db:
        db.collection("notification_consents").document(uid).set(update_data, merge=True)
        # Disable channel in preferences
        db.collection("notification_preferences").document(uid).set({
            f"{pref_key}_enabled": False,
            "updated_at": firestore.SERVER_TIMESTAMP,
        }, merge=True)

    logger.info(f"User {uid} opted out of {pref_key}.")
    return {"success": True, "message": f"Successfully opted out of {pref_key} alerts."}
