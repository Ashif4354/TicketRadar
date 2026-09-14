# src/Backend/api/routers/consent.py

import logging
from fastapi import APIRouter, HTTPException, Depends, Request
from google.cloud import firestore

from lib.core.auth import get_authorized_user, db
from lib.utils.phone import normalize_indian_phone
from api.schemas import OptInRequest
from api.dependencies import verify_recaptcha

logger = logging.getLogger("ticketradar.api.consent")

router = APIRouter(prefix="/api/consent", tags=["Consent"])

VALID_MEDIUMS = ("whatsapp", "sms", "phone_call", "call", "email", "discord", "discord_webhook")


@router.post("/{medium}/opt-in")
async def opt_in_medium(
    medium: str,
    request: Request,
    payload: OptInRequest = None,
    claims: dict = Depends(get_authorized_user)
):
    """Records explicit consent for notification channels (WhatsApp, SMS, Call, Email, Discord)."""
    uid = claims.get("uid")
    medium_clean = medium.strip().lower().replace(" ", "_")
    if medium_clean not in VALID_MEDIUMS:
        raise HTTPException(status_code=400, detail=f"Unsupported consent medium: {medium}")

    # Verify reCAPTCHA token (mandatory when security is enabled)
    await verify_recaptcha(payload.recaptcha_token if payload else None)

    if medium_clean in ("call", "phone_call"):
        consent_key = "call"
        pref_key = "phone_call"
    elif medium_clean in ("discord", "discord_webhook"):
        consent_key = "discord"
        pref_key = "discord"
    else:
        consent_key = medium_clean
        pref_key = medium_clean

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
    pref_update = {
        f"{pref_key}_enabled": True,
        "updated_at": firestore.SERVER_TIMESTAMP,
    }

    if payload:
        if payload.phone_number and consent_key in ("sms", "whatsapp", "call"):
            try:
                phone_e164 = normalize_indian_phone(payload.phone_number)
                update_data["phone_number"] = phone_e164
            except ValueError as ve:
                raise HTTPException(status_code=400, detail=str(ve))
        elif payload.email_address and consent_key == "email":
            email_clean = payload.email_address.strip()
            update_data["email_address"] = email_clean
            pref_update["email_address"] = email_clean
        elif payload.webhook_url and consent_key == "discord":
            hook_clean = payload.webhook_url.strip()
            update_data["discord_webhook_url"] = hook_clean
            pref_update["discord_webhook_url"] = hook_clean

    if db:
        db.collection("notification_consents").document(uid).set(update_data, merge=True)
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
    if medium_clean not in VALID_MEDIUMS:
        raise HTTPException(status_code=400, detail=f"Unsupported consent medium: {medium}")

    if medium_clean in ("call", "phone_call"):
        consent_key = "call"
        pref_key = "phone_call"
    elif medium_clean in ("discord", "discord_webhook"):
        consent_key = "discord"
        pref_key = "discord"
    else:
        consent_key = medium_clean
        pref_key = medium_clean

    update_data = {
        "uid": uid,
        f"{consent_key}_consented": False,
        f"{consent_key}_revoked_at": firestore.SERVER_TIMESTAMP,
        f"{pref_key}_consented": False,
        "updated_at": firestore.SERVER_TIMESTAMP,
    }

    if db:
        db.collection("notification_consents").document(uid).set(update_data, merge=True)
        db.collection("notification_preferences").document(uid).set({
            f"{pref_key}_enabled": False,
            "updated_at": firestore.SERVER_TIMESTAMP,
        }, merge=True)

    logger.info(f"User {uid} opted out of {pref_key}.")
    return {"success": True, "message": f"Successfully opted out of {pref_key} alerts."}
