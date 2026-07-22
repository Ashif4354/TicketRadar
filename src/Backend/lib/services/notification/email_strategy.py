# src/services/notification/email_strategy.py

from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import List
import aiosmtplib
from .base import NotificationStrategy
from ...utils.config import settings

class EmailNotificationStrategy(NotificationStrategy):
    """
    Concrete strategy to send notifications via email asynchronously, displaying availability in a table.
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
        url: str
    ) -> tuple[bool, str]:
        if not self.recipient_email:
            return False, "Recipient email is missing."

        # Setup standard MIME multipart message
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = settings.smtp_email
        msg["To"] = self.recipient_email

        # Build table rows for HTML and text output
        rows_html = ""
        rows_text = ""
        
        for t in available_theatres:
            rows_html += f"""
            <tr style="background-color: rgba(16, 185, 129, 0.05);">
              <td style="padding: 12px; border: 1px solid #374151; font-weight: 600; color: #f3f4f6;">{t}</td>
              <td style="padding: 12px; border: 1px solid #374151; text-align: center; color: #34d399; font-weight: 700;">🟢 Available</td>
            </tr>
            """
            rows_text += f"{t: <40} | AVAILABLE\n"
            
        for t in unavailable_theatres:
            rows_html += f"""
            <tr style="background-color: rgba(239, 68, 68, 0.02);">
              <td style="padding: 12px; border: 1px solid #374151; color: #9ca3af; text-decoration: line-through;">{t}</td>
              <td style="padding: 12px; border: 1px solid #374151; text-align: center; color: #f87171;">🔴 Unavailable</td>
            </tr>
            """
            rows_text += f"{t: <40} | UNAVAILABLE\n"

        # Add resume note if there are remaining unavailable theatres
        resume_note_text = ""
        resume_note_html = ""
        if unavailable_theatres:
            resume_note_text = "\nNote: Monitoring has paused for this alert. If you still want to monitor for the remaining unavailable theatres, please resume your tracker from the dashboard.\n"
            resume_note_html = """
                <div style="margin-top: 15px; padding: 12px 16px; background-color: rgba(245, 158, 11, 0.1); border-left: 4px solid #f59e0b; border-radius: 6px; font-size: 13px; color: #fbbf24; line-height: 1.5;">
                  ℹ️ <strong>Note:</strong> Monitoring has paused for this alert. If you still want to monitor for the remaining unavailable theatres, please resume your tracker from the dashboard.
                </div>
            """

        # Text body template (Strictly no "please")
        text_body = (
            f"TicketRadar: Booking Open!\n\n"
            f"Movie: {movie_name}\n"
            f"Date: {date_str}\n"
            f"Link: {url}\n\n"
            f"Theatre Availability:\n"
            f"{'-'*55}\n"
            f"{'Theatre Name': <40} | {'Status': <12}\n"
            f"{'-'*55}\n"
            f"{rows_text}"
            f"{'-'*55}\n"
            f"{resume_note_text}\n"
            f"Book tickets immediately."
        )

        # HTML body template (Strictly no "please")
        html_body = f"""
        <html>
          <body style="font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background-color: #0e1117; color: #ffffff; padding: 20px;">
            <div style="max-width: 650px; margin: 0 auto; background-color: #1f2937; border: 1px solid #374151; border-radius: 12px; overflow: hidden; box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);">
              <div style="background: linear-gradient(135deg, #ec4899, #ef4444); padding: 20px; text-align: center;">
                <h1 style="margin: 0; color: #ffffff; font-size: 24px; font-weight: 700;">🍿 Booking Open!</h1>
                <p style="margin: 5px 0 0 0; color: #f3f4f6; font-size: 16px; font-weight: 600;">{movie_name}</p>
              </div>
              <div style="padding: 24px; line-height: 1.6; font-size: 16px; color: #d1d5db;">
                <p style="margin-top: 0;">Booking is now open for <strong>{movie_name}</strong> on the target date <strong>{date_str}</strong>.</p>
                
                <h3 style="color: #ffffff; margin-top: 20px; margin-bottom: 10px;">🏢 Theatre Availability</h3>
                <table style="width: 100%; border-collapse: collapse; margin-bottom: 15px; font-size: 14px;">
                  <thead>
                    <tr style="background-color: #111827; color: #ffffff;">
                      <th style="padding: 12px; border: 1px solid #374151; text-align: left;">Theatre Name</th>
                      <th style="padding: 12px; border: 1px solid #374151; text-align: center; width: 140px;">Status</th>
                    </tr>
                  </thead>
                  <tbody>
                    {rows_html}
                  </tbody>
                </table>
                
                {resume_note_html}

                <div style="margin-top: 25px; text-align: center;">
                  <a href="{url}" target="_blank" style="background: linear-gradient(135deg, #ec4899, #ef4444); color: white; padding: 12px 24px; text-decoration: none; border-radius: 8px; font-weight: 600; display: inline-block; box-shadow: 0 4px 12px rgba(236, 72, 153, 0.3);">Book Tickets Now 🔗</a>
                </div>
              </div>
              <div style="background-color: #111827; padding: 15px; text-align: center; border-top: 1px solid #374151; font-size: 12px; color: #9ca3af;">
                This notification was sent automatically by TicketRadar.
              </div>
            </div>
          </body>
        </html>
        """

        part_text = MIMEText(text_body, "plain")
        part_html = MIMEText(html_body, "html")
        msg.attach(part_text)
        msg.attach(part_html)

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
