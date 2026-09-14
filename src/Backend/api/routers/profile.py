# src/Backend/api/routers/profile.py

import logging
from fastapi import APIRouter, HTTPException, Depends
from google.cloud import firestore

from lib.core.auth import get_authorized_user, db
from lib.services.wallet import WalletService
from lib.services.terms import TermsService
from lib.utils.phone import normalize_indian_phone
from lib.utils.config import settings
from api.dependencies import get_user_details, verify_recaptcha
from api.schemas import UpdateNotificationPreferencesRequest

logger = logging.getLogger("ticketradar.api.profile")

router = APIRouter(prefix="/api/profile", tags=["Profile"])


@router.get("")
async def get_profile(claims: dict = Depends(get_authorized_user)):
    """
    Returns the user's complete profile, notification preferences,
    consent records, terms acceptance status, and wallet balance.
    """
    uid = claims.get("uid")
    if not uid:
        raise HTTPException(status_code=401, detail="User identification missing.")

    name, email, photo_url = get_user_details(uid, claims)

    # 1. Fetch user doc
    user_data = {}
    if db:
        u_doc = db.collection("users").document(uid).get()
        if u_doc.exists:
            user_data = u_doc.to_dict() or {}

    # 2. Fetch notification preferences
    prefs = {
        "uid": uid,
        "email_enabled": True,
        "email_address": email,
        "discord_enabled": False,
        "discord_webhook_url": None,
        "whatsapp_enabled": False,
        "whatsapp_phone": None,
        "phone_call_enabled": False,
        "call_phone": None,
        "sms_enabled": False,
        "sms_phone": None,
        "email_fallback_on_no_answer": True,
        "preferred_medium": "email",
    }
    if db:
        p_doc = db.collection("notification_preferences").document(uid).get()
        if p_doc.exists:
            prefs.update(p_doc.to_dict() or {})

    # 3. Fetch consents
    consents = {
        "whatsapp_consented": False,
        "sms_consented": False,
        "call_consented": False,
        "email_consented": False,
        "discord_consented": False,
    }
    if db:
        c_doc = db.collection("notification_consents").document(uid).get()
        if c_doc.exists:
            cdata = c_doc.to_dict() or {}
            consents["whatsapp_consented"] = cdata.get("whatsapp_consented", False)
            consents["sms_consented"] = cdata.get("sms_consented", False)
            consents["call_consented"] = cdata.get("call_consented", False)
            consents["email_consented"] = cdata.get("email_consented", False)
            consents["discord_consented"] = cdata.get("discord_consented", False)

    # 4. Fetch wallet balance if payments are enabled
    wallet_balance = 0
    disable_payments = settings.disable_payments if settings else False
    if not disable_payments:
        wallet_balance = WalletService.get_balance(uid)

    terms_accepted = TermsService.check_terms_accepted(uid)

    primary_phone = (
        user_data.get("phone_number")
        or prefs.get("sms_phone")
        or prefs.get("whatsapp_phone")
        or prefs.get("call_phone")
    )
    primary_discord = prefs.get("discord_webhook_url")
    primary_email = prefs.get("email_address") or email

    return {
        "uid": uid,
        "email": email,
        "displayName": name,
        "photoUrl": photo_url,
        "phone_number": primary_phone,
        "discord_webhook_url": primary_discord,
        "email_medium_address": primary_email,
        "terms_version_accepted": user_data.get("terms_version_accepted"),
        "terms_accepted": terms_accepted,
        "preferences": prefs,
        "consents": consents,
        "wallet_balance_paise": wallet_balance,
        "wallet_balance_inr": round(wallet_balance / 100.0, 2),
    }


@router.put("/preferences")
@router.post("/preferences")
async def update_preferences(
    payload: UpdateNotificationPreferencesRequest,
    claims: dict = Depends(get_authorized_user)
):
    """
    Updates the user's notification preferences document.
    Validates Indian phone numbers for SMS, WhatsApp, and Voice if updated.
    Correctly clears Discord webhook URL or email when empty string/null is provided.
    Requires and verifies reCAPTCHA.
    """
    uid = claims.get("uid")
    if not uid:
        raise HTTPException(status_code=401, detail="User identification missing.")

    # Verify reCAPTCHA token (mandatory when security is enabled)
    await verify_recaptcha(payload.recaptcha_token if payload else None)

    update_dict = {}
    normalized_phone = None
    clear_phone = False

    raw_data = payload.model_dump(exclude_unset=True)

    for k, v in raw_data.items():
        if k == "recaptcha_token":
            continue

        if k in ("whatsapp_phone", "call_phone", "sms_phone", "phone_number"):
            if v and str(v).strip():
                try:
                    norm = normalize_indian_phone(v)
                    update_dict[k] = norm
                    if k == "phone_number":
                        normalized_phone = norm
                except ValueError as e:
                    raise HTTPException(status_code=400, detail=str(e))
            else:
                update_dict[k] = firestore.DELETE_FIELD
                if k == "phone_number":
                    clear_phone = True
        elif k == "discord_webhook_url":
            clean_url = str(v).strip() if v is not None else ""
            update_dict[k] = clean_url if clean_url else firestore.DELETE_FIELD
        elif k == "email_address":
            clean_email = str(v).strip() if v is not None else ""
            update_dict[k] = clean_email if clean_email else firestore.DELETE_FIELD
        else:
            update_dict[k] = v

    if normalized_phone:
        if "sms_phone" not in update_dict:
            update_dict["sms_phone"] = normalized_phone
        if "whatsapp_phone" not in update_dict:
            update_dict["whatsapp_phone"] = normalized_phone
        if "call_phone" not in update_dict:
            update_dict["call_phone"] = normalized_phone
    elif clear_phone:
        update_dict["sms_phone"] = firestore.DELETE_FIELD
        update_dict["whatsapp_phone"] = firestore.DELETE_FIELD
        update_dict["call_phone"] = firestore.DELETE_FIELD
        update_dict["phone_number"] = firestore.DELETE_FIELD

    update_dict["uid"] = uid

    if db:
        db.collection("notification_preferences").document(uid).set({
            **update_dict,
            "updated_at": firestore.SERVER_TIMESTAMP
        }, merge=True)
        if normalized_phone:
            db.collection("users").document(uid).set({
                "phone_number": normalized_phone,
                "updated_at": firestore.SERVER_TIMESTAMP
            }, merge=True)
        elif clear_phone:
            db.collection("users").document(uid).set({
                "phone_number": firestore.DELETE_FIELD,
                "updated_at": firestore.SERVER_TIMESTAMP
            }, merge=True)

    from datetime import datetime, timezone
    return_dict = {k: (None if v == firestore.DELETE_FIELD else v) for k, v in update_dict.items()}
    return_dict["updated_at"] = datetime.now(timezone.utc).isoformat()
    return {"success": True, "preferences": return_dict}
