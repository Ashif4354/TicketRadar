# src/Backend/lib/services/notification/email_strategy.py

from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.utils import formataddr
from typing import List
import aiosmtplib

from .base import NotificationStrategy
from .templates.email import EmailTemplates
from ...utils.config import settings


class EmailNotificationStrategy(NotificationStrategy, EmailTemplates):
    """
    Concrete strategy to send notifications via email asynchronously.
    Inherits template rendering capabilities from EmailTemplates.
    """

    def __init__(self, recipient_email: str):
        self.recipient_email = recipient_email

    async def send_notification(
        self,
        subject: str,
        movie_name: str,
        date_str: str,
        available_theatres: List[str],
        unavailable_theatres: List[str],
        url: str,
        language: str = "",
        format_name: str = ""
    ) -> tuple[bool, str]:
        """
        Asynchronously send a detailed email notification listing theatre availability.
        Uses EmailTemplates to render modern HTML and plain-text output.
        """
        if not self.recipient_email:
            return False, "Recipient email is missing."

        rendered = self.get_template(
            "booking_alert",
            movie_name=movie_name,
            date_str=date_str,
            available_theatres=available_theatres,
            unavailable_theatres=unavailable_theatres,
            url=url,
            language=language,
            format_name=format_name,
            subject=subject
        )

        msg = MIMEMultipart("alternative")
        msg["Subject"] = rendered["subject"]
        msg["From"] = formataddr(("TicketRadar", settings.smtp_email))
        msg["To"] = self.recipient_email

        part_text = MIMEText(rendered["text_body"], "plain")
        part_html = MIMEText(rendered["html_body"], "html")
        msg.attach(part_text)
        msg.attach(part_html)

        import os
        env = (os.getenv("ENVIRONMENT") or (getattr(settings, "environment", "") if settings else "")).strip().lower()
        if env == "test":
            return True, "Skipped in test environment."

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
            return True, "Email sent successfully."
        except Exception as e:
            return False, f"Failed to send email: {str(e)}"
