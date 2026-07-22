# src/Backend/api/dependencies.py

import logging
import httpx
from fastapi import HTTPException
from lib.utils.config import settings
from lib.core.auth import auth as firebase_auth

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
    if not token:
        raise HTTPException(status_code=400, detail="reCAPTCHA token is required.")

    recaptcha_url = "https://www.google.com/recaptcha/api/siteverify"
    secret_key = settings.recaptcha_secret if settings else "6LfUdl0tAAAAAAjyjVtoGRY2cY52NJUOhc4R3mLu"

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
