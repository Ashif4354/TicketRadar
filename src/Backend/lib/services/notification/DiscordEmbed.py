# src/Backend/lib/services/notification/DiscordEmbed.py

import os
import logging
from typing import List, Optional, Dict, Any
from datetime import datetime, timezone
import httpx

from ...utils.config import settings

logger = logging.getLogger("ticketradar.discord_embed")


class DiscordEmbed:
    """
    Encapsulates Discord webhook embed construction and dispatching.
    Provides unified HTTP handling via httpx.AsyncClient for both admin alerts
    and user notification strategies.
    """

    def __init__(
        self,
        title: Optional[str] = None,
        description: Optional[str] = None,
        color: Optional[int] = None,
        fields: Optional[List[Dict[str, Any]]] = None,
        thumbnail_url: Optional[str] = None,
        footer_text: Optional[str] = None,
        footer_icon_url: Optional[str] = None,
        timestamp: Optional[datetime] = None,
    ):
        self.title = title
        self.description = description
        self.color = color
        self.fields: List[Dict[str, Any]] = list(fields) if fields else []
        self.thumbnail_url = thumbnail_url
        self.footer_text = footer_text
        self.footer_icon_url = footer_icon_url
        self.timestamp = timestamp or datetime.now(timezone.utc)

    def add_field(self, name: str, value: str, inline: bool = True) -> "DiscordEmbed":
        """Adds a field to the embed."""
        self.fields.append({"name": str(name), "value": str(value), "inline": inline})
        return self

    def set_thumbnail(self, url: str) -> "DiscordEmbed":
        """Sets thumbnail URL."""
        self.thumbnail_url = url
        return self

    def set_footer(self, text: str, icon_url: Optional[str] = None) -> "DiscordEmbed":
        """Sets footer text and optional icon."""
        self.footer_text = text
        self.footer_icon_url = icon_url
        return self

    def to_dict(self) -> Dict[str, Any]:
        """Converts embed parameters to a Discord embed dictionary."""
        embed: Dict[str, Any] = {}
        if self.title:
            embed["title"] = self.title
        if self.description:
            embed["description"] = self.description
        if self.color is not None:
            embed["color"] = self.color
        if self.timestamp:
            embed["timestamp"] = (
                self.timestamp.isoformat()
                if isinstance(self.timestamp, datetime)
                else str(self.timestamp)
            )
        if self.footer_text:
            footer: Dict[str, Any] = {"text": self.footer_text}
            if self.footer_icon_url:
                footer["icon_url"] = self.footer_icon_url
            embed["footer"] = footer
        if self.thumbnail_url and self.thumbnail_url.startswith("http"):
            embed["thumbnail"] = {"url": self.thumbnail_url}
        if self.fields:
            embed["fields"] = self.fields
        return embed

    def to_payload(self) -> Dict[str, Any]:
        """Returns standard Discord webhook JSON payload dict."""
        return {"embeds": [self.to_dict()]}

    async def send(self, webhook_url: str, timeout: float = 10.0) -> tuple[bool, str]:
        """Sends this embed to the given Discord webhook URL."""
        return await self.send_payload(webhook_url, self.to_payload(), timeout=timeout)

    @classmethod
    async def send_payload(
        cls,
        webhook_url: str,
        payload: Dict[str, Any],
        timeout: float = 10.0
    ) -> tuple[bool, str]:
        """
        Dispatches a raw or template-rendered Discord webhook payload.
        Suppresses external network calls when running in test mode (ENVIRONMENT=test).
        """
        if not webhook_url or not webhook_url.strip():
            logger.debug("Discord webhook URL is missing or empty. Skipping dispatch.")
            return False, "Discord Webhook URL is missing."

        env = (
            os.getenv("ENVIRONMENT")
            or (getattr(settings, "environment", "") if settings else "")
        ).strip().lower()
        if env == "test":
            logger.debug("Test environment detected. Skipping Discord webhook dispatch.")
            return True, "Skipped in test environment."

        try:
            async with httpx.AsyncClient() as client:
                resp = await client.post(webhook_url.strip(), json=payload, timeout=timeout)
                if resp.status_code in (200, 204):
                    logger.info("Discord notification sent successfully.")
                    return True, "Discord notification sent successfully."
                else:
                    err_msg = f"Discord webhook status {resp.status_code}: {resp.text}"
                    logger.error(err_msg)
                    return False, err_msg
        except Exception as e:
            err_msg = f"Failed to send Discord notification: {e}"
            logger.error(err_msg)
            return False, err_msg

    @classmethod
    async def send_embed(
        cls,
        webhook_url: str,
        title: str,
        description: str,
        color: int = 0x7C3AED,
        fields: Optional[List[Dict[str, Any]]] = None,
        thumbnail_url: Optional[str] = None,
        footer_text: Optional[str] = "TicketRadar Admin Alerts",
        timeout: float = 10.0
    ) -> tuple[bool, str]:
        """Convenience method to construct and send an embed in one call."""
        embed = cls(
            title=title,
            description=description,
            color=color,
            fields=fields,
            thumbnail_url=thumbnail_url,
            footer_text=footer_text
        )
        return await embed.send(webhook_url, timeout=timeout)
