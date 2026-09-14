# src/Backend/lib/services/notification/sms_strategy.py

from typing import List, Optional
from .base import NotificationStrategy
from .templates.message import MessageTemplates
from ...providers.notification.base import NotificationProviderAdapter


class SMSNotificationStrategy(NotificationStrategy, MessageTemplates):
    """
    Delivers movie ticket availability alerts via SMS using the NotificationProviderAdapter.
    Inherits template rendering capabilities from MessageTemplates.
    """

    def __init__(
        self,
        phone_number: str,
        provider: NotificationProviderAdapter,
        job_id: Optional[str] = None
    ):
        self._phone_number = phone_number.strip()
        self._provider = provider
        self._job_id = job_id or "job"

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
        rendered = self.get_template(
            "booking_alert",
            movie_name=movie_name,
            date_str=date_str,
            available_theatres=available_theatres,
            unavailable_theatres=unavailable_theatres,
            url=url,
            language=language,
            format_name=format_name
        )

        body = rendered["body"]
        idempotency_key = f"sms_{self._job_id}_{date_str}"
        result = await self._provider.send_sms(
            to=self._phone_number,
            body=body,
            idempotency_key=idempotency_key
        )

        if result.success:
            return True, f"SMS submitted successfully (SID: {result.provider_id})"
        else:
            return False, result.error_message or "Failed to deliver SMS alert."
