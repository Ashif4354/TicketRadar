# src/Backend/lib/providers/notification/factory.py

from typing import Dict, Type
from .base import NotificationProviderAdapter
from .twilio_adapter import TwilioProviderAdapter
from ...utils.config import settings

class NotificationProviderFactory:
    """
    Returns the configured notification provider adapter.
    Provider selected via NOTIFICATION_PROVIDER setting/env var (default: 'twilio').
    """

    _registry: Dict[str, Type[NotificationProviderAdapter]] = {
        "twilio": TwilioProviderAdapter,
    }

    @classmethod
    def register_provider(cls, name: str, adapter_cls: Type[NotificationProviderAdapter]) -> None:
        cls._registry[name.lower()] = adapter_cls

    @classmethod
    def create(cls) -> NotificationProviderAdapter:
        provider_name = (settings.notification_provider if settings else "twilio").strip().lower()
        adapter_cls = cls._registry.get(provider_name)
        if not adapter_cls:
            raise ValueError(f"Unknown notification provider: {provider_name}")

        if adapter_cls is TwilioProviderAdapter:
            return TwilioProviderAdapter(
                account_sid=settings.twilio_account_sid if settings else "",
                auth_token=settings.twilio_auth_token if settings else "",
                from_number=settings.twilio_phone_number if settings else "",
                whatsapp_content_sid=settings.twilio_whatsapp_content_sid if settings else "",
            )

        return adapter_cls()
