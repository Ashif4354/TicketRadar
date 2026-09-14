# src/Backend/lib/services/notification/factory.py

from typing import Optional, Dict, Any
from .base import NotificationStrategy
from .email_strategy import EmailNotificationStrategy
from .discord_strategy import DiscordWebhookNotificationStrategy
from .sms_strategy import SMSNotificationStrategy
from .whatsapp_strategy import WhatsAppNotificationStrategy
from .phone_call_strategy import PhoneCallNotificationStrategy
from ...providers.notification.factory import NotificationProviderFactory
from ...providers.notification.base import NotificationProviderAdapter

class NotificationStrategyFactory:
    """
    Factory pattern class to instantiate the correct NotificationStrategy based on configuration.
    Injects NotificationProviderAdapter into SMS, WhatsApp, and Phone Call strategies.
    """

    @staticmethod
    def create_strategy(
        medium: str,
        config: Dict[str, Any],
        provider_adapter: Optional[NotificationProviderAdapter] = None,
        job_id: Optional[str] = None
    ) -> NotificationStrategy:
        """
        Creates a concrete notification strategy.
        
        Args:
            medium (str): 'email', 'discord', 'sms', 'whatsapp', or 'phone_call'.
            config (dict): Configuration options for the selected strategy.
            provider_adapter (NotificationProviderAdapter, optional): Optional mock or custom adapter.
            job_id (str, optional): Job ID for callback and tracking.
        
        Returns:
            NotificationStrategy: An instance of a concrete strategy.
        """
        norm_medium = medium.strip().lower().replace(" ", "_")
        if norm_medium == "email":
            email = config.get("recipient_email", "").strip()
            return EmailNotificationStrategy(email)
        elif norm_medium in ("discord", "discord_webhook"):
            webhook_url = config.get("webhook_url", "").strip()
            return DiscordWebhookNotificationStrategy(webhook_url)
        elif norm_medium == "sms":
            phone = config.get("phone_number") or config.get("phone", "")
            provider = provider_adapter or NotificationProviderFactory.create()
            return SMSNotificationStrategy(phone_number=phone, provider=provider, job_id=job_id)
        elif norm_medium == "whatsapp":
            phone = config.get("phone_number") or config.get("phone", "")
            content_sid = config.get("content_sid")
            provider = provider_adapter or NotificationProviderFactory.create()
            return WhatsAppNotificationStrategy(phone_number=phone, provider=provider, content_sid=content_sid, job_id=job_id)
        elif norm_medium in ("phone_call", "call"):
            phone = config.get("phone_number") or config.get("phone", "")
            base_url = config.get("base_url")
            provider = provider_adapter or NotificationProviderFactory.create()
            return PhoneCallNotificationStrategy(phone_number=phone, provider=provider, base_url=base_url, job_id=job_id)
        else:
            raise ValueError(f"Unknown notification medium: {medium}. Supported types are email, discord, sms, whatsapp, phone_call")
