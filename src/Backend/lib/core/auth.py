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

DEV_MOCK_CLAIMS = {
    "uid": "dev-user-001",
    "email": "dev@ticketradar.local",
    "name": "Dev Admin",
    "displayName": "Dev Admin",
    "picture": "",
    "photoUrl": "",
    "authorized": True,
    "role": "admin",
    "blocked": False,
}


def is_security_disabled() -> bool:
    """Checks whether security verification is globally disabled."""
    return (
        os.getenv("DISABLE_SECURITY", "false").lower() in ("true", "1") or
        (settings and getattr(settings, "disable_security", False))
    )


def is_approval_disabled() -> bool:
    """Checks whether approval / authorization gating is globally disabled."""
    return (
        os.getenv("DISABLE_APPROVAL", "false").lower() in ("true", "1") or
        (settings and getattr(settings, "disable_approval", False))
    )


def get_environment() -> str:
    """
    Returns the active environment ('development', 'production', 'test').
    If security is globally disabled (DISABLE_SECURITY=true), automatically forces 'development'
    unless running in 'test' mode.
    """
    if is_security_disabled():
        current = (os.getenv("ENVIRONMENT") or (getattr(settings, "environment", None) if settings else "")).strip().lower()
        if current == "test":
            return "test"
        return "development"

    env = os.getenv("ENVIRONMENT")
    if not env and settings:
        env = getattr(settings, "environment", None)
    return (env or "development").strip().lower()


async def verify_app_check(x_firebase_appcheck: str = Header(None, alias="X-Firebase-AppCheck")):
    """Verifies the Firebase App Check token to ensure calls originate from the client app."""
    disable_security = (
        is_security_disabled() or
        os.getenv("DISABLE_APP_CHECK", "false").lower() in ("true", "1")
    )
    env = get_environment()
    is_dev = env in ("development", "test")

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
    When security is disabled, bypasses token verification and provides mock admin claims.
    """
    if is_security_disabled():
        logger.debug("Bypassing authentication as security is disabled.")
        claims = None
        if authorization and authorization.startswith("Bearer "):
            token = authorization.split("Bearer ")[1].strip()
            if token:
                try:
                    claims = auth.verify_id_token(token)
                    claims = dict(claims)
                except Exception:
                    try:
                        import jwt
                        decoded = jwt.decode(token, options={"verify_signature": False})
                        if isinstance(decoded, dict) and (decoded.get("uid") or decoded.get("user_id") or decoded.get("sub")):
                            claims = dict(decoded)
                            if "uid" not in claims:
                                claims["uid"] = claims.get("user_id") or claims.get("sub")
                    except Exception:
                        pass

        if not claims:
            claims = DEV_MOCK_CLAIMS.copy()
        else:
            claims["authorized"] = True
            claims["role"] = "admin"
            claims["blocked"] = False
        return claims

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

    # 3. Check if user is blocked (bypassed if approval gating is disabled)
    if claims.get("blocked", False) and not is_approval_disabled():
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
    When security or approval gating is disabled, bypasses authorization check.
    """
    if is_security_disabled():
        res = dict(claims or DEV_MOCK_CLAIMS)
        res["authorized"] = True
        res["role"] = "admin"
        res["blocked"] = False
        return res
    if is_approval_disabled():
        res = dict(claims or DEV_MOCK_CLAIMS)
        res["authorized"] = True
        res["blocked"] = False
        return res
    if not claims.get("authorized", False):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User is not authorized to access the app content."
        )
    return claims

async def get_admin_user(claims: dict = Depends(get_current_user_claims)):
    """
    Verifies that the user has the 'admin' role custom claim.
    When security is disabled, admin panel is disabled.
    """
    if is_security_disabled():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin panel is disabled because DISABLE_SECURITY is true"
        )
    if claims.get("role") != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied. User is not an admin."
        )
    return claims
