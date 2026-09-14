# src/Backend/lib/services/notification/phone_call_strategy.py

from typing import List, Optional
from .base import NotificationStrategy
from ...providers.notification.base import NotificationProviderAdapter
from ...utils.config import settings

class PhoneCallNotificationStrategy(NotificationStrategy):
    """
    Delivers movie ticket availability alerts via an automated Voice Phone Call
    using Amazon Polly (en-IN) TTS via the NotificationProviderAdapter.
    """

    def __init__(
        self,
        phone_number: str,
        provider: NotificationProviderAdapter,
        base_url: Optional[str] = None,
        job_id: Optional[str] = None
    ):
        self._phone_number = phone_number.strip()
        self._provider = provider
        self._base_url = (base_url or (settings.app_base_url if settings else "http://localhost:8000")).rstrip("/")
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
        twiml_url = f"{self._base_url}/api/twilio/voice-twiml/{self._job_id}"
        status_callback_url = f"{self._base_url}/api/twilio/call-status"
        idempotency_key = f"call_{self._job_id}_{date_str}"

        result = await self._provider.initiate_call(
            to=self._phone_number,
            twiml_or_answer_url=twiml_url,
            status_callback_url=status_callback_url,
            idempotency_key=idempotency_key
        )

        if result.success:
            return True, f"Phone call initiated successfully (Call SID: {result.call_id})"
        else:
            return False, result.error_message or "Failed to initiate phone call alert."
