# src/Backend/api/routers/config.py

import logging
from fastapi import APIRouter, HTTPException, Depends
from lib.utils.config import settings, config_error
from lib.core.auth import get_authorized_user, is_security_disabled
from lib.services.notification.factory import NotificationStrategyFactory
from lib.services.pricing import PricingService
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
        "payment_gateway": settings.payment_gateway if settings else "cashfree",
        "notification_provider": settings.notification_provider if settings else "twilio",
    }


@router.post("/test-notification")
async def test_notification(payload: TestAlertRequest, claims: dict = Depends(get_authorized_user)):
    """Sends a test alert to verify connection details."""
    medium = payload.medium.lower().replace(" ", "_")
    target = payload.target.strip()

    if not target:
        raise HTTPException(status_code=400, detail="Target recipient/URL/phone is required.")

    if "email" in medium:
        notif_type = "email"
    elif "discord" in medium:
        notif_type = "discord"
    elif "sms" in medium:
        notif_type = "sms"
    elif "whatsapp" in medium:
        notif_type = "whatsapp"
    elif "call" in medium or "phone" in medium:
        notif_type = "phone_call"
    else:
        raise HTTPException(status_code=400, detail=f"Unsupported notification medium: {payload.medium}")

    # Validate that test notifications are only allowed for mediums defined as free (0 Rs) by the admin
    price_paise, _ = PricingService.get_price_for_medium(notif_type)
    if price_paise > 0:
        gcp_logger.log_event(
            "Test Notification Blocked",
            user_id=claims.get("uid"),
            details={
                "medium": payload.medium,
                "notif_type": notif_type,
                "price_paise": price_paise,
                "reason": "Medium is not defined free (0 Rs) by admin",
            },
            level="WARNING",
        )
        raise HTTPException(
            status_code=400,
            detail=f"Test notifications are only allowed for free mediums (₹0) defined by the administrator. '{payload.medium}' is currently configured as a paid medium (₹{price_paise / 100:.2f}).",
        )

    # Verify reCAPTCHA token
    await verify_recaptcha(payload.recaptcha_token)

    from lib.utils.phone import normalize_indian_phone

    if notif_type == "email":
        config = {"recipient_email": target}
    elif notif_type == "discord":
        config = {"webhook_url": target}
    elif notif_type == "sms":
        try:
            norm_phone = normalize_indian_phone(target)
        except ValueError as ve:
            raise HTTPException(status_code=400, detail=str(ve))
        config = {"phone_number": norm_phone}
    elif notif_type == "whatsapp":
        try:
            norm_phone = normalize_indian_phone(target)
        except ValueError as ve:
            raise HTTPException(status_code=400, detail=str(ve))
        config = {"phone_number": norm_phone}
    elif notif_type == "phone_call":
        try:
            norm_phone = normalize_indian_phone(target)
        except ValueError as ve:
            raise HTTPException(status_code=400, detail=str(ve))
        config = {"phone_number": norm_phone}

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
