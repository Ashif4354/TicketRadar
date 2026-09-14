# src/Backend/lib/services/notification/discord_strategy.py

import httpx
from typing import List
from .base import NotificationStrategy
from .templates.discord import DiscordTemplates


class DiscordWebhookNotificationStrategy(NotificationStrategy, DiscordTemplates):
    """
    Concrete strategy to send notifications via Discord Webhooks asynchronously.
    Inherits template rendering capabilities from DiscordTemplates.
    """

    def __init__(self, webhook_url: str):
        self.webhook_url = webhook_url

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
        Send a Discord webhook notification containing movie and theatre availability details.
        Uses DiscordTemplates to render formatted ASCII tables and rich embeds.
        """
        if not self.webhook_url:
            return False, "Discord Webhook URL is missing."

        payload = self.get_template(
            "booking_alert",
            subject=subject,
            movie_name=movie_name,
            date_str=date_str,
            available_theatres=available_theatres,
            unavailable_theatres=unavailable_theatres,
            url=url,
            language=language,
            format_name=format_name
        )

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(self.webhook_url, json=payload, timeout=10.0)
                if response.status_code in (200, 204):
                    return True, "Discord notification sent successfully."
                else:
                    return False, f"Discord Webhook returned code {response.status_code}: {response.text}"
        except Exception as e:
            return False, f"Failed to send Discord notification: {str(e)}"
