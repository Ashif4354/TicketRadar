# src/Backend/api/dependencies.py

import logging
import httpx
from fastapi import HTTPException
from lib.utils.config import settings
from lib.core.auth import (
    auth as firebase_auth,
    get_current_user_claims,
    get_authorized_user,
    get_admin_user,
    DEV_MOCK_CLAIMS,
    is_security_disabled,
)

logger = logging.getLogger("ticketradar.api")


def get_user_details(uid: str = None, claims: dict = None) -> tuple[str, str, str]:
    """Helper to extract user display name, email, and photo URL from claims or Firebase Auth."""
    name = ""
    email = ""
    photo_url = ""

    if claims:
        email = claims.get("email", "")
        name = claims.get("name", "") or claims.get("displayName", "")
        photo_url = claims.get("picture", "") or claims.get("photoUrl", "")
        if not uid:
            uid = claims.get("uid")

    if is_security_disabled():
        if uid == "dev-user-001" or (claims and claims.get("uid") == "dev-user-001"):
            return name or "Dev Admin", email or "dev@ticketradar.local", photo_url or ""
        email = email or (f"{uid}@ticketradar.local" if uid else "dev@ticketradar.local")
        name = name or (email.split("@")[0] if email else "Dev User")
        return name, email, photo_url or ""

    if uid and (not name or not email or not photo_url):
        try:
            u = firebase_auth.get_user(uid)
            email = email or u.email or ""
            name = name or u.display_name or ""
            photo_url = photo_url or u.photo_url or ""
        except Exception as e:
            logger.debug(f"Failed to fetch user from Firebase Auth ({uid}): {e}")

    if not name and email:
        name = email.split("@")[0]
    elif not name:
        name = "User"

    return name, email, photo_url


async def verify_recaptcha(token: str):
    """Verifies a reCAPTCHA v2 token with Google's siteverify API."""
    if is_security_disabled():
        logger.debug("reCAPTCHA verification bypassed as security is disabled.")
        return True

    if not token:
        raise HTTPException(status_code=400, detail="reCAPTCHA token is required.")

    recaptcha_url = "https://www.google.com/recaptcha/api/siteverify"
    secret_key = (settings.recaptcha_secret if settings else "") or os.getenv("RECAPTCHA_SECRET", "")
    if not secret_key:
        logger.error("RECAPTCHA_SECRET is not configured on the backend server.")
        raise HTTPException(status_code=500, detail="Server security configuration error (reCAPTCHA secret missing).")

    try:
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                recaptcha_url,
                data={
                    "secret": secret_key,
                    "response": token
                }
            )
            resp_data = resp.json()
            if not resp_data.get("success"):
                logger.warning(f"reCAPTCHA validation failed: {resp_data}")
                raise HTTPException(status_code=400, detail="reCAPTCHA verification failed.")
    except httpx.HTTPError as e:
        logger.error(f"reCAPTCHA verification request failed: {e}")
        raise HTTPException(status_code=500, detail="Unable to verify reCAPTCHA with Google servers.")


def require_payments_enabled():
    """Dependency that ensures payment and wallet operations are enabled."""
    import os
    is_disabled = (
        os.getenv("DISABLE_PAYMENTS", "").lower() in ("true", "1")
        or (settings and getattr(settings, "disable_payments", False))
    )
    if is_disabled:
        raise HTTPException(
            status_code=503,
            detail="Payment features are disabled (DISABLE_PAYMENTS=true)."
        )


async def require_terms_accepted(claims: dict = None):
    """Checks that user has accepted current terms version before proceeding."""
    if is_security_disabled():
        return True

    from lib.services.terms import TermsService
    uid = claims.get("uid") if claims else None
    if uid and not TermsService.check_terms_accepted(uid):
        raise HTTPException(
            status_code=403,
            detail="You must accept the updated Terms of Service (v2.0) to use this feature."
        )
    return True

