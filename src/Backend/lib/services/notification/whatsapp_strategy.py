# src/Backend/lib/services/notification/whatsapp_strategy.py

from typing import List, Optional
from .base import NotificationStrategy
from ...providers.notification.base import NotificationProviderAdapter

class WhatsAppNotificationStrategy(NotificationStrategy):
    """
    Delivers movie ticket availability alerts via WhatsApp using approved templates
    through the NotificationProviderAdapter.
    """

    def __init__(
        self,
        phone_number: str,
        provider: NotificationProviderAdapter,
        content_sid: Optional[str] = None,
        job_id: Optional[str] = None
    ):
        self._phone_number = phone_number.strip()
        self._provider = provider
        self._content_sid = content_sid or ""
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
        # Formatted movie title with language/format if present
        fmt_str = f" ({language} {format_name})".strip() if (language or format_name) else ""
        full_title = f"{movie_name}{fmt_str}"

        variables = {
            "1": full_title,
            "2": date_str,
            "3": url,
            "movie_name": full_title,
            "date_str": date_str,
            "url": url,
        }

        idempotency_key = f"wa_{self._job_id}_{date_str}"
        result = await self._provider.send_whatsapp_template(
            to=self._phone_number,
            template_id=self._content_sid,
            template_variables=variables,
            idempotency_key=idempotency_key
        )

        if result.success:
            return True, f"WhatsApp alert submitted successfully (SID: {result.provider_id})"
        else:
            return False, result.error_message or "Failed to deliver WhatsApp alert."
