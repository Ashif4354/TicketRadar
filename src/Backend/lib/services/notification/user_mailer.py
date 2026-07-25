# src/Backend/lib/services/notification/user_mailer.py

import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.utils import formataddr
import aiosmtplib

from ...utils.config import settings

logger = logging.getLogger("ticketradar.user_mailer")


async def send_user_access_granted_email(recipient_email: str, user_name: str) -> tuple[bool, str]:
    """
    Sends a welcome / access granted email to the user when their access request is approved by an administrator.
    """
    if not recipient_email:
        return False, "Recipient email is missing."

    if not settings or not getattr(settings, "smtp_email", None) or not getattr(settings, "smtp_password", None):
        logger.warning("SMTP is not configured. Skipping access granted email.")
        return False, "SMTP is not configured."

    display_name = user_name or recipient_email.split("@")[0] or "User"
    subject = "Welcome to TicketRadar — Access Granted! 🎉"

    text_body = (
        f"Hi {display_name},\n\n"
        f"Great news! Your access request for TicketRadar has been approved by an administrator.\n\n"
        f"You can now log in to your account and start setting up instant ticket trackers for movies, shows, and events.\n\n"
        f"Account Email: {recipient_email}\n"
        f"Status: Authorized ✅\n\n"
        f"Happy Tracking!\n"
        f"The TicketRadar Team"
    )

    html_body = f"""
    <html>
      <body style="font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background-color: #0e1117; color: #ffffff; padding: 20px;">
        <div style="max-width: 600px; margin: 0 auto; background-color: #1f2937; border: 1px solid #374151; border-radius: 12px; overflow: hidden; box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);">
          <div style="background: linear-gradient(135deg, #10b981, #ec4899); padding: 24px; text-align: center;">
            <h1 style="margin: 0; color: #ffffff; font-size: 24px; font-weight: 700;">🍿 Access Granted!</h1>
            <p style="margin: 6px 0 0 0; color: #f3f4f6; font-size: 15px; font-weight: 500;">Welcome to TicketRadar</p>
          </div>
          <div style="padding: 28px; line-height: 1.6; font-size: 15px; color: #d1d5db;">
            <p style="margin-top: 0;">Hi <strong>{display_name}</strong>,</p>
            <p>Great news! Your access request for <strong>TicketRadar</strong> has been approved by an administrator.</p>

            <div style="margin: 20px 0; padding: 16px; background-color: rgba(16, 185, 129, 0.1); border-left: 4px solid #10b981; border-radius: 6px; font-size: 14px; color: #34d399;">
              🎉 <strong>Status: Account Authorized</strong><br>
              You now have full access to create ticket availability trackers, receive instant alerts, and configure notifications.
            </div>

            <h4 style="color: #ffffff; margin-top: 20px; margin-bottom: 10px;">What you can do next:</h4>
            <ul style="padding-left: 20px; margin: 0 0 20px 0; color: #d1d5db; font-size: 14px;">
              <li style="margin-bottom: 8px;">🎬 Track movie showtimes on BookMyShow for target dates & theatres</li>
              <li style="margin-bottom: 8px;">🔔 Receive instant alerts via Email or Discord Webhook as soon as tickets open</li>
              <li style="margin-bottom: 8px;">⚡ Monitor availability automatically in the background</li>
            </ul>
          </div>
          <div style="background-color: #111827; padding: 16px; text-align: center; border-top: 1px solid #374151; font-size: 12px; color: #9ca3af;">
            TicketRadar • Real-time Ticket Availability Tracker
          </div>
        </div>
      </body>
    </html>
    """

    return await _send_email(recipient_email, subject, text_body, html_body)


async def _send_email(to_email: str, subject: str, text_body: str, html_body: str) -> tuple[bool, str]:
    """Helper to send an email via SMTP asynchronously."""
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = formataddr(("TicketRadar", settings.smtp_email))
    msg["To"] = to_email

    msg.attach(MIMEText(text_body, "plain"))
    msg.attach(MIMEText(html_body, "html"))

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
        logger.info(f"Sent transactional email '{subject}' to {to_email}")
        return True, "Email sent successfully."
    except Exception as e:
        logger.error(f"Failed to send transactional email to {to_email}: {e}")
        return False, f"Failed to send email: {str(e)}"
