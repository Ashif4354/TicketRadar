# src/services/notification/discord_strategy.py

import httpx
from typing import List
from src.Backend.services.notification.base import NotificationStrategy

class DiscordWebhookNotificationStrategy(NotificationStrategy):
    """
    Concrete strategy to send notifications via Discord Webhooks asynchronously, displaying availability in a table.
    """

    def __init__(self, webhook_url: str):
        self.webhook_url = webhook_url

    def _generate_ascii_table(self, available: List[str], unavailable: List[str]) -> str:
        """Generates a clean ASCII table representing theatre availability."""
        header_name = "Theatre Name"
        header_status = "Status"
        
        # Grid boundaries
        lines = []
        border = "+-------------------------------------+-------------+"
        lines.append(border)
        lines.append(f"| {header_name: <35} | {header_status: <11} |")
        lines.append(border)
        
        for t in available:
            # Truncate if exceeds column width
            t_trunc = t[:35]
            lines.append(f"| {t_trunc: <35} | AVAILABLE   |")
            lines.append(border)
            
        for t in unavailable:
            t_trunc = t[:35]
            lines.append(f"| {t_trunc: <35} | UNAVAILABLE |")
            lines.append(border)
            
        return "\n".join(lines)

    async def send_notification(
        self,
        subject: str,
        movie_name: str,
        date_str: str,
        available_theatres: List[str],
        unavailable_theatres: List[str],
        url: str
    ) -> tuple[bool, str]:
        if not self.webhook_url:
            return False, "Discord Webhook URL is missing."

        # Compile the ASCII table
        ascii_table = self._generate_ascii_table(available_theatres, unavailable_theatres)

        # Build embed description text (Strictly no "please")
        description = (
            f"**Movie:** {movie_name}\n"
            f"**Date:** {date_str}\n"
            f"**Booking Link:** [Click here to book]({url})\n\n"
            f"**Theatre Availability Table:**\n"
            f"```text\n"
            f"{ascii_table}\n"
            f"```\n"
            f"Book tickets immediately."
        )

        # Build a beautiful rich embed payload for Discord
        payload = {
            "embeds": [
                {
                    "title": f"🍿 {subject}",
                    "description": description,
                    "color": 0xEC4899,  # Premium Pink color (#ec4899)
                    "thumbnail": {
                        "url": "https://images.unsplash.com/photo-1517604931442-7e0c8ed2963c?w=100&auto=format&fit=crop&q=60"
                    },
                    "footer": {
                        "text": "TicketRadar"
                    }
                }
            ]
        }

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(self.webhook_url, json=payload, timeout=10.0)
                
                # Discord webhook post success responds with either 200 (OK) or 204 (No Content)
                if response.status_code in (200, 204):
                    return True, "Discord notification sent successfully."
                else:
                    return False, f"Discord Webhook returned code {response.status_code}: {response.text}"
        except Exception as e:
            return False, f"Failed to send Discord notification: {str(e)}"
