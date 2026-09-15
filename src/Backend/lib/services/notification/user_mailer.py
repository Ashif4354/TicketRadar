# src/Backend/lib/services/notification/user_mailer.py

import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.utils import formataddr
from typing import Optional, List, Dict, Any
import aiosmtplib

from .templates.email import EmailTemplates
from ...utils.config import settings

logger = logging.getLogger("ticketradar.user_mailer")


async def _send_rendered_email(to_email: str, template_name: str, **context: Any) -> tuple[bool, str]:
    """Helper to render an EmailTemplate and dispatch it via SMTP asynchronously."""
    if not to_email or not to_email.strip():
        return False, "Recipient email is missing."

    import os
    env = (os.getenv("ENVIRONMENT") or (getattr(settings, "environment", "") if settings else "")).strip().lower()
    if env == "test":
        logger.debug(f"Test environment detected. Skipping email '{template_name}' to {to_email}.")
        return True, "Skipped in test environment."

    if not settings or not getattr(settings, "smtp_email", None) or not getattr(settings, "smtp_password", None):
        logger.warning(f"SMTP is not configured. Skipping email '{template_name}' to {to_email}.")
        return False, "SMTP is not configured."

    try:
        ctx = {"recipient_email": to_email.strip(), "user_email": to_email.strip()}
        ctx.update(context)
        rendered = EmailTemplates.get_template(template_name, **ctx)
    except Exception as te:
        logger.error(f"Failed to render email template '{template_name}': {te}")
        return False, f"Template render error: {te}"

    msg = MIMEMultipart("alternative")
    msg["Subject"] = rendered["subject"]
    msg["From"] = formataddr(("TicketRadar", settings.smtp_email))
    msg["To"] = to_email.strip()

    msg.attach(MIMEText(rendered["text_body"], "plain"))
    msg.attach(MIMEText(rendered["html_body"], "html"))

    from ...utils.apm import async_capture_span

    async with async_capture_span(
        f"email.transactional.{template_name}",
        span_type="notification.email",
        labels={"template": template_name, "to": to_email.strip()}
    ) as span:
        try:
            await aiosmtplib.send(
                msg,
                hostname=settings.smtp_server,
                port=settings.smtp_port,
                username=settings.smtp_email,
                password=settings.smtp_password,
                start_tls=True,
                timeout=15.0
            )
            if span:
                span.set_success()
            logger.info(f"Dispatched email '{template_name}' to {to_email}")
            return True, "Email sent successfully."
        except Exception as e:
            if span:
                span.set_failure()
            logger.error(f"Failed to send email '{template_name}' to {to_email}: {e}")
            return False, f"Failed to send email: {str(e)}"


# 1. Access Granted Email
async def send_user_access_granted_email(recipient_email: str, user_name: str) -> tuple[bool, str]:
    return await _send_rendered_email(
        to_email=recipient_email,
        template_name="access_granted",
        recipient_email=recipient_email,
        user_name=user_name
    )


# 2. Signup / First Login Email
async def send_signup_email(recipient_email: str, user_name: str, app_url: Optional[str] = None) -> tuple[bool, str]:
    base_url = (app_url or (settings.app_base_url if settings else "http://localhost:8000")).rstrip("/")
    return await _send_rendered_email(
        to_email=recipient_email,
        template_name="signup",
        user_name=user_name,
        email=recipient_email,
        app_url=base_url
    )


# 3. Payment Successful Email
async def send_payment_success_email(
    recipient_email: str,
    user_name: str,
    order_id: str,
    amount_inr: float,
    payment_id: str = "",
    payment_type: str = "Wallet Top-up"
) -> tuple[bool, str]:
    return await _send_rendered_email(
        to_email=recipient_email,
        template_name="payment_success",
        user_name=user_name,
        order_id=order_id,
        amount_inr=amount_inr,
        payment_id=payment_id,
        payment_type=payment_type
    )


# 4. Payment Failed Email
async def send_payment_failed_email(
    recipient_email: str,
    user_name: str,
    order_id: str,
    amount_inr: float,
    failure_reason: str = "Payment was declined or cancelled."
) -> tuple[bool, str]:
    return await _send_rendered_email(
        to_email=recipient_email,
        template_name="payment_failed",
        user_name=user_name,
        order_id=order_id,
        amount_inr=amount_inr,
        failure_reason=failure_reason
    )


# 5. Call Unanswered (3 Attempts) Email
async def send_call_unanswered_email(
    recipient_email: str,
    user_name: str,
    phone_number: str,
    movie_name: str,
    date_str: str,
    available_theatres: Optional[List[str]] = None,
    url: str = "",
    attempt_count: int = 3
) -> tuple[bool, str]:
    return await _send_rendered_email(
        to_email=recipient_email,
        template_name="call_unanswered",
        user_name=user_name,
        phone_number=phone_number,
        movie_name=movie_name,
        date_str=date_str,
        available_theatres=available_theatres or [],
        url=url,
        attempt_count=attempt_count
    )


# 6. Call Success (Voice Call Answered) Email
async def send_call_success_email(
    recipient_email: str,
    user_name: str,
    phone_number: str,
    movie_name: str,
    date_str: str,
    call_duration_seconds: int = 0,
    url: str = ""
) -> tuple[bool, str]:
    return await _send_rendered_email(
        to_email=recipient_email,
        template_name="call_success",
        user_name=user_name,
        phone_number=phone_number,
        movie_name=movie_name,
        date_str=date_str,
        call_duration_seconds=call_duration_seconds,
        url=url
    )


# 7. Wallet Topup Success Email
async def send_wallet_topup_success_email(
    recipient_email: str,
    user_name: str,
    amount_inr: float,
    new_balance_inr: float,
    order_id: str = ""
) -> tuple[bool, str]:
    return await _send_rendered_email(
        to_email=recipient_email,
        template_name="wallet_topup_success",
        user_name=user_name,
        amount_inr=amount_inr,
        new_balance_inr=new_balance_inr,
        order_id=order_id
    )


# 8. Wallet Topup Failed Email
async def send_wallet_topup_failed_email(
    recipient_email: str,
    user_name: str,
    amount_inr: float,
    order_id: str = "",
    reason: str = "Payment declined"
) -> tuple[bool, str]:
    return await _send_rendered_email(
        to_email=recipient_email,
        template_name="wallet_topup_failed",
        user_name=user_name,
        amount_inr=amount_inr,
        order_id=order_id,
        reason=reason
    )


# 9. Wallet Transaction Email
async def send_wallet_transaction_email(
    recipient_email: str,
    user_name: str,
    txn_type: str,
    direction: str,
    amount_inr: float,
    new_balance_inr: float,
    description: str = ""
) -> tuple[bool, str]:
    return await _send_rendered_email(
        to_email=recipient_email,
        template_name="wallet_transaction",
        user_name=user_name,
        txn_type=txn_type,
        direction=direction,
        amount_inr=amount_inr,
        new_balance_inr=new_balance_inr,
        description=description
    )


# 10. Refund Email
async def send_refund_email(
    recipient_email: str,
    user_name: str,
    amount_inr: float,
    reason: str,
    job_id: str = "",
    new_balance_inr: float = 0.0
) -> tuple[bool, str]:
    return await _send_rendered_email(
        to_email=recipient_email,
        template_name="refund",
        user_name=user_name,
        amount_inr=amount_inr,
        reason=reason,
        job_id=job_id,
        new_balance_inr=new_balance_inr
    )


# 11. Admin Pricing Changed Email
async def send_admin_pricing_changed_email(
    admin_email: str,
    admin_name: str,
    old_prices: Optional[Dict[str, Any]],
    new_prices: Optional[Dict[str, Any]],
    note: str
) -> tuple[bool, str]:
    return await _send_rendered_email(
        to_email=admin_email,
        template_name="admin_pricing_changed",
        admin_name=admin_name,
        admin_email=admin_email,
        old_prices=old_prices,
        new_prices=new_prices,
        note=note
    )


# 12. Job Created Email
async def send_job_created_email(
    recipient_email: str,
    user_name: str,
    job_id: str,
    movie_name: str,
    date_str: str,
    theatres: Optional[List[str]] = None,
    notification_medium: str = "Email",
    check_interval: int = 60
) -> tuple[bool, str]:
    return await _send_rendered_email(
        to_email=recipient_email,
        template_name="job_created",
        user_name=user_name,
        job_id=job_id,
        movie_name=movie_name,
        date_str=date_str,
        theatres=theatres or [],
        notification_medium=notification_medium,
        check_interval=check_interval
    )


# 13. Job Cancelled Email
async def send_job_cancelled_email(
    recipient_email: str,
    user_name: str,
    job_id: str,
    movie_name: str,
    refund_amount_inr: float = 0.0
) -> tuple[bool, str]:
    return await _send_rendered_email(
        to_email=recipient_email,
        template_name="job_cancelled",
        user_name=user_name,
        job_id=job_id,
        movie_name=movie_name,
        refund_amount_inr=refund_amount_inr
    )


# 14. Notification Sent Email
async def send_notification_sent_email(
    recipient_email: str,
    user_name: str,
    movie_name: str,
    notification_medium: str = "",
    available_theatres: Optional[List[str]] = None
) -> tuple[bool, str]:
    return await _send_rendered_email(
        to_email=recipient_email,
        template_name="notification_sent",
        user_name=user_name,
        movie_name=movie_name,
        notification_medium=notification_medium,
        available_theatres=available_theatres or []
    )


# 15. Notification Failed Email
async def send_notification_failed_email(
    recipient_email: str,
    user_name: str,
    job_id: str,
    movie_name: str,
    notification_medium: str = "",
    error_message: str = "",
    refunded: bool = True
) -> tuple[bool, str]:
    return await _send_rendered_email(
        to_email=recipient_email,
        template_name="notification_failed",
        user_name=user_name,
        job_id=job_id,
        movie_name=movie_name,
        notification_medium=notification_medium,
        error_message=error_message,
        refunded=refunded
    )

