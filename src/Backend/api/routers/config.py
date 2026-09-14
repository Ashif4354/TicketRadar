# src/Backend/api/routers/config.py

import logging
from fastapi import APIRouter, HTTPException, Depends
from lib.utils.config import settings, config_error
from lib.core.auth import get_authorized_user, is_security_disabled
from lib.services.notification.factory import NotificationStrategyFactory
from lib.services.gcp_logger import gcp_logger
from api.schemas import TestAlertRequest
from api.dependencies import verify_recaptcha

logger = logging.getLogger("ticketradar.api")

router = APIRouter(prefix="/api", tags=["Config"])


@router.get("/config")
async def get_config():
    """Retrieve application configuration and validation error status."""
    import os
    from lib.core.auth import is_approval_disabled, get_environment
    disable_sec = is_security_disabled()
    disable_pay = os.getenv("DISABLE_PAYMENTS", "").lower() in ("true", "1") or (settings and getattr(settings, "disable_payments", False))
    disable_appr = is_approval_disabled()
    return {
        "config_error": config_error,
        "environment": get_environment(),
        "smtp_server": settings.smtp_server if settings else None,
        "smtp_email": settings.smtp_email if settings else None,
        "default_check_interval": settings.default_check_interval if settings else 60,
        "disable_security": disable_sec,
        "disable_payments": disable_pay,
        "disable_approval": disable_appr,
    }


@router.post("/test-notification")
async def test_notification(payload: TestAlertRequest, claims: dict = Depends(get_authorized_user)):
    """Sends a test alert to verify connection details."""
    medium = payload.medium.lower().replace(" ", "_")
    target = payload.target.strip()

    if not target:
        raise HTTPException(status_code=400, detail="Target recipient/URL/phone is required.")

    # Verify reCAPTCHA token
    await verify_recaptcha(payload.recaptcha_token)

    from lib.utils.phone import normalize_indian_phone

    if "email" in medium:
        config = {"recipient_email": target}
        notif_type = "email"
    elif "discord" in medium:
        config = {"webhook_url": target}
        notif_type = "discord"
    elif "sms" in medium:
        try:
            norm_phone = normalize_indian_phone(target)
        except ValueError as ve:
            raise HTTPException(status_code=400, detail=str(ve))
        config = {"phone_number": norm_phone}
        notif_type = "sms"
    elif "whatsapp" in medium:
        try:
            norm_phone = normalize_indian_phone(target)
        except ValueError as ve:
            raise HTTPException(status_code=400, detail=str(ve))
        config = {"phone_number": norm_phone}
        notif_type = "whatsapp"
    elif "call" in medium or "phone" in medium:
        try:
            norm_phone = normalize_indian_phone(target)
        except ValueError as ve:
            raise HTTPException(status_code=400, detail=str(ve))
        config = {"phone_number": norm_phone}
        notif_type = "phone_call"
    else:
        raise HTTPException(status_code=400, detail=f"Unsupported notification medium: {payload.medium}")

    try:
        notifier = NotificationStrategyFactory.create_strategy(notif_type, config)
        success, msg = await notifier.send_notification(
            subject="Test Alert",
            movie_name="Test Movie",
            date_str="20260719",
            available_theatres=["Sample Theatre A", "Sample Theatre B"],
            unavailable_theatres=["Sample Theatre C"],
            url="https://in.bookmyshow.com"
        )
        if success:
            gcp_logger.log_event(
                "Test Notification Sent",
                user_id=claims.get("uid"),
                details={"medium": medium, "target": target, "status": "SUCCESS"}
            )
            return {"success": True, "message": "Test notification sent successfully!"}
        else:
            gcp_logger.log_event(
                "Test Notification Failed",
                user_id=claims.get("uid"),
                details={"medium": medium, "target": target, "error": msg},
                level="WARNING"
            )
            return {"success": False, "message": msg}
    except Exception as err:
        gcp_logger.log_event(
            "Test Notification Error",
            user_id=claims.get("uid"),
            details={"medium": medium, "target": target},
            level="ERROR",
            exception=err
        )
        return {"success": False, "message": str(err)}
