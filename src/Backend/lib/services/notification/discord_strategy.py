# src/Backend/lib/services/notification/discord_strategy.py

from typing import List
from .base import NotificationStrategy
from .templates.discord import DiscordTemplates
from .DiscordEmbed import DiscordEmbed


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

        return await DiscordEmbed.send_payload(self.webhook_url, payload)
