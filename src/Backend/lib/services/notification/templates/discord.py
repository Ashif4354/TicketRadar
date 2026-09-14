# src/Backend/lib/services/notification/templates/discord.py

from typing import Dict, Any, List, Optional
from datetime import datetime, timezone


class DiscordTemplates:
    """
    Centralized Discord webhook template catalog.
    Provides get_template function returning Discord webhook payload dict with embeds.
    Can be inherited by DiscordWebhookNotificationStrategy.
    """

    @staticmethod
    def _generate_ascii_table(available: List[str], unavailable: List[str]) -> str:
        """Generates a clean ASCII table representing theatre availability."""
        header_name = "Theatre Name"
        header_status = "Status"

        lines = []
        border = "+-------------------------------------+-------------+"
        lines.append(border)
        lines.append(f"| {header_name: <35} | {header_status: <11} |")
        lines.append(border)

        for t in available:
            t_trunc = t[:35]
            lines.append(f"| {t_trunc: <35} | AVAILABLE   |")
            lines.append(border)

        for t in unavailable:
            t_trunc = t[:35]
            lines.append(f"| {t_trunc: <35} | UNAVAILABLE |")
            lines.append(border)

        return "\n".join(lines)

    @classmethod
    def get_template(cls, template_name: str, **context: Any) -> Dict[str, Any]:
        """
        Retrieves and renders a Discord webhook payload by template name.

        Args:
            template_name: The identifier of the template.
            **context: Context variables.

        Returns:
            Dict representing Discord webhook payload {"embeds": [...]}.
        """
        norm_name = template_name.strip().lower().replace("-", "_")

        renderers = {
            "booking_alert": cls._render_booking_alert,
            "alert": cls._render_booking_alert,
            "job_created": cls._render_job_created,
            "job_cancelled": cls._render_job_cancelled,
            "notification_sent": cls._render_notification_sent,
            "notification_failed": cls._render_notification_failed,
        }

        renderer = renderers.get(norm_name)
        if not renderer:
            # Fallback embed
            return {
                "embeds": [{
                    "title": f"🍿 TicketRadar: {template_name}",
                    "description": context.get("description", "Notification update."),
                    "color": 0xEC4899,
                    "footer": {"text": "TicketRadar"}
                }]
            }

        return renderer(**context)

    @classmethod
    def _render_booking_alert(
        cls,
        subject: str = "Booking Open!",
        movie_name: str = "Movie",
        date_str: str = "",
        available_theatres: Optional[List[str]] = None,
        unavailable_theatres: Optional[List[str]] = None,
        url: str = "",
        language: str = "",
        format_name: str = "",
        **kwargs: Any
    ) -> Dict[str, Any]:
        available = available_theatres or ([kwargs["cinema_name"]] if "cinema_name" in kwargs else [])
        unavailable = unavailable_theatres or []
        booking_url = url or kwargs.get("booking_url", "")

        ascii_table = cls._generate_ascii_table(available, unavailable)

        resume_note = ""
        if unavailable:
            resume_note = "\nℹ️ **Note:** Monitoring has paused for this alert. If you still want to monitor for the remaining unavailable theatres, resume your tracker from the dashboard.\n"

        fmt_details = " | ".join(filter(None, [language, format_name, kwargs.get("details", "")]))
        format_line = f"**Format & Language:** {fmt_details}\n" if fmt_details else ""

        description = (
            f"**Movie:** {movie_name}\n"
            f"{format_line}"
            f"**Date:** {date_str}\n"
            f"**Booking Link:** [Click here to book]({booking_url})\n\n"
            f"**Theatre Availability Table:**\n"
            f"```text\n"
            f"{ascii_table}\n"
            f"```\n"
            f"{resume_note}\n"
            f"Book tickets immediately."
        )

        title_text = f"🎬 TicketRadar Alert: {movie_name}" if ("Alert" in subject or subject == "Booking Open!") else f"🍿 {subject}"

        return {
            "embeds": [
                {
                    "title": title_text,
                    "description": description,
                    "color": 0xEC4899,  # Premium Pink color (#ec4899)
                    "thumbnail": {
                        "url": "https://images.unsplash.com/photo-1517604931442-7e0c8ed2963c?w=100&auto=format&fit=crop&q=60"
                    },
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "footer": {
                        "text": "TicketRadar"
                    }
                }
            ]
        }

    @classmethod
    def _render_job_created(
        cls,
        movie_name: str = "",
        date_str: str = "",
        job_id: str = "",
        theatres: Optional[List[str]] = None,
        **kwargs: Any
    ) -> Dict[str, Any]:
        th_str = ", ".join((theatres or [])[:3])
        return {
            "embeds": [
                {
                    "title": "🎯 New Ticket Tracker Created",
                    "description": f"Monitoring **{movie_name}** on **{date_str}**.\nCinemas: {th_str}",
                    "color": 0x3B82F6,
                    "fields": [
                        {"name": "Job ID", "value": job_id, "inline": True},
                        {"name": "Status", "value": "Active", "inline": True},
                    ],
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "footer": {"text": "TicketRadar"}
                }
            ]
        }

    @classmethod
    def _render_job_cancelled(
        cls,
        movie_name: str = "",
        job_id: str = "",
        **kwargs: Any
    ) -> Dict[str, Any]:
        return {
            "embeds": [
                {
                    "title": "⏸️ Tracker Stopped / Cancelled",
                    "description": f"Monitoring for **{movie_name}** (Job #{job_id}) has been stopped.",
                    "color": 0xF97316,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "footer": {"text": "TicketRadar"}
                }
            ]
        }

    @classmethod
    def _render_notification_sent(
        cls,
        movie_name: str = "",
        notification_medium: str = "",
        **kwargs: Any
    ) -> Dict[str, Any]:
        return {
            "embeds": [
                {
                    "title": "🔔 Availability Notification Dispatched",
                    "description": f"Alert sent via **{notification_medium}** for **{movie_name}**.",
                    "color": 0x10B981,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "footer": {"text": "TicketRadar"}
                }
            ]
        }

    @classmethod
    def _render_notification_failed(
        cls,
        movie_name: str = "",
        job_id: str = "",
        error_message: str = "",
        **kwargs: Any
    ) -> Dict[str, Any]:
        return {
            "embeds": [
                {
                    "title": "⚠️ Alert Delivery Failed",
                    "description": f"Failed to deliver alert for **{movie_name}** (Job #{job_id}).\nError: {error_message}",
                    "color": 0xEF4444,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "footer": {"text": "TicketRadar"}
                }
            ]
        }
