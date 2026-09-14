# src/Backend/lib/services/notification/sms_strategy.py

from typing import List, Optional
from .base import NotificationStrategy
from ...providers.notification.base import NotificationProviderAdapter
from ...utils.redact import redact_phone

class SMSNotificationStrategy(NotificationStrategy):
    """
    Delivers movie ticket availability alerts via SMS using the NotificationProviderAdapter.
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
        theatres_summary = ", ".join(available_theatres[:3])
        if len(available_theatres) > 3:
            theatres_summary += f" +{len(available_theatres) - 3} more"

        fmt_desc = f" ({language} {format_name})".strip() if (language or format_name) else ""
        body = (
            f"🎬 TicketRadar Alert: Tickets open for {movie_name}{fmt_desc} on {date_str}!\n"
            f"Cinemas: {theatres_summary}\n"
            f"Book now: {url}"
        )

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
