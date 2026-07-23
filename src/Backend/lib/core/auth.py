# src/Backend/core/auth.py

import os
import logging
import firebase_admin
from firebase_admin import credentials, auth, app_check, firestore
from fastapi import Header, HTTPException, status, Depends
from ..utils.config import settings
from ..services.gcp_logger import gcp_logger

logger = logging.getLogger("ticketradar.auth")


# Initialize Firebase Admin SDK
if not firebase_admin._apps:
    try:
        cred_dict = {
            "type": settings.firebase_type,
            "project_id": settings.firebase_project_id,
            "private_key_id": settings.firebase_private_key_id,
            "private_key": settings.firebase_private_key.replace("\\n", "\n") if settings.firebase_private_key else "",
            "client_email": settings.firebase_client_email,
            "client_id": settings.firebase_client_id,
            "auth_uri": settings.firebase_auth_uri,
            "token_uri": settings.firebase_token_uri,
            "auth_provider_x509_cert_url": settings.firebase_auth_provider_x509_cert_url,
            "client_x509_cert_url": settings.firebase_client_x509_cert_url,
            "universe_domain": settings.universe_domain if hasattr(settings, "universe_domain") else settings.firebase_universe_domain
        }
        if cred_dict["project_id"] and cred_dict["private_key"]:
            cred = credentials.Certificate(cred_dict)
            firebase_admin.initialize_app(cred)
            logger.info("Firebase Admin SDK successfully initialized from environment variables.")
        else:
            firebase_admin.initialize_app()
            logger.warning("Firebase Admin SDK initialized using default credentials (missing env configuration).")
    except Exception as e:
        logger.error(f"Failed to initialize Firebase Admin SDK: {e}")
        try:
            firebase_admin.initialize_app()
            logger.info("Firebase Admin SDK fallback initialized using default credentials.")
        except Exception as ex:
            logger.error(f"Fallback initialization failed: {ex}")

# Initialize Firestore Client
db = None
try:
    db = firestore.client()
    logger.info("Firestore client initialized successfully.")
except Exception as e:
    logger.error(f"Failed to initialize Firestore client: {e}")

async def verify_app_check(x_firebase_appcheck: str = Header(None, alias="X-Firebase-AppCheck")):
    """Verifies the Firebase App Check token to ensure calls originate from the client app."""
    disable_security = (
        os.getenv("DISABLE_SECURITY", "false").lower() in ("true", "1") or
        os.getenv("DISABLE_APP_CHECK", "false").lower() in ("true", "1") or
        (settings and getattr(settings, "disable_security", False))
    )
    is_dev = os.getenv("ENVIRONMENT", "development").lower() == "development"

    if disable_security:
        logger.debug("Bypassing Firebase App Check as security is disabled.")
        return

    if not x_firebase_appcheck:
        if is_dev:
            logger.warning("Missing X-Firebase-AppCheck header — bypassing check in development mode.")
            return
        logger.warning("Missing X-Firebase-AppCheck header.")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="App Check token is required."
        )
    try:
        app_check.verify_token(x_firebase_appcheck)
    except Exception as e:
        if is_dev:
            logger.warning(f"App Check verification failed ({e}) — bypassing check in development mode.")
            return
        logger.error(f"App Check verification failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired App Check token."
        )

async def get_current_user_claims(
    authorization: str = Header(None),
    x_firebase_appcheck: str = Header(None, alias="X-Firebase-AppCheck")
):
    """
    Verifies App Check, checks authentication, and returns user claims.
    Blocks users if the 'blocked' custom claim is True.
    """
    # 1. Enforce App Check
    await verify_app_check(x_firebase_appcheck)

    # 2. Verify JWT ID token
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or invalid authentication credentials."
        )
    
    token = authorization.split("Bearer ")[1]
    try:
        claims = auth.verify_id_token(token)
    except Exception as e:
        logger.error(f"Firebase token verification failed: {e}")
        gcp_logger.log_event("Authentication Failed", user_id="unauthenticated", details={"reason": str(e)}, level="WARNING")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid or expired ID token: {e}"
        )

    # 3. Check if user is blocked
    if claims.get("blocked", False):
        user_uid = claims.get("uid") or "unknown"
        gcp_logger.log_event("Blocked User Access Attempt", user_id=user_uid, details={"email": claims.get("email")}, level="WARNING")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User is blocked and cannot access the app content."
        )

    return claims

async def get_authorized_user(claims: dict = Depends(get_current_user_claims)):
    """
    Verifies that the user has the 'authorized' custom claim set to True.
    """
    if not claims.get("authorized", False):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User is not authorized to access the app content."
        )
    return claims

async def get_admin_user(claims: dict = Depends(get_current_user_claims)):
    """
    Verifies that the user has the 'admin' role custom claim.
    """
    if claims.get("role") != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied. User is not an admin."
        )
    return claims
