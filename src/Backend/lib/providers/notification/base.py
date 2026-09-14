# src/Backend/lib/providers/notification/base.py

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional, Dict, Any

@dataclass
class ProviderMessageResult:
    success: bool
    provider_id: str
    error_code: Optional[str] = None
    error_message: Optional[str] = None

@dataclass
class ProviderCallResult:
    success: bool
    call_id: str
    error_code: Optional[str] = None
    error_message: Optional[str] = None

class NotificationProviderAdapter(ABC):
    """
    Abstraction over third-party notification SDKs (Twilio, Plivo, etc.).
    All methods are async and must:
    - Never raise on provider errors — return ProviderMessageResult(success=False, ...)
    - Never log PII (phone numbers, message body with user data)
    """

    @abstractmethod
    async def send_sms(
        self,
        to: str,
        body: str,
        idempotency_key: str,
    ) -> ProviderMessageResult:
        """Send an SMS message to an E.164 formatted phone number."""
        pass

    @abstractmethod
    async def send_whatsapp_template(
        self,
        to: str,
        template_id: str,
        template_variables: Dict[str, Any],
        idempotency_key: str,
    ) -> ProviderMessageResult:
        """Send an approved WhatsApp template to an E.164 formatted phone number."""
        pass

    @abstractmethod
    async def initiate_call(
        self,
        to: str,
        twiml_or_answer_url: str,
        status_callback_url: str,
        idempotency_key: str,
    ) -> ProviderCallResult:
        """Initiate an outbound phone call."""
        pass

    @abstractmethod
    def validate_incoming_webhook(
        self,
        raw_body: bytes,
        headers: Dict[str, str],
        url: str,
    ) -> bool:
        """Validate signature of incoming provider webhook."""
        pass

    @abstractmethod
    def parse_message_status_event(self, form_data: Dict[str, Any]) -> Dict[str, Any]:
        """Parse status callback payload for SMS/WhatsApp."""
        pass

    @abstractmethod
    def parse_call_status_event(self, form_data: Dict[str, Any]) -> Dict[str, Any]:
        """Parse status callback payload for Voice calls."""
        pass
