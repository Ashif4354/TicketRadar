# src/Backend/lib/providers/payment/base.py

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, Dict, Any

class OrderStatus(str, Enum):
    PENDING = "pending"
    SUCCESS = "success"
    FAILED = "failed"
    EXPIRED = "expired"

@dataclass
class OrderResult:
    order_id: str
    session_token: str
    checkout_url: Optional[str] = None

@dataclass
class RefundResult:
    success: bool
    refund_id: str
    provider_refund_id: Optional[str] = None
    error_message: Optional[str] = None

@dataclass
class WebhookEvent:
    event_type: str
    order_id: str
    payment_id: Optional[str] = None
    refund_id: Optional[str] = None
    amount_paise: int = 0
    raw: Dict[str, Any] = field(default_factory=dict)

class PaymentGateway(ABC):
    """
    Abstraction over payment gateway providers (Cashfree, Razorpay, Stripe, etc.).
    All implementations must:
    - Return typed result objects (never raw provider dicts to callers)
    - Validate webhook signatures before parsing
    - Handle all provider-specific errors internally
    - Never leak provider internals or secrets to callers
    """

    @abstractmethod
    async def create_order(
        self,
        amount_paise: int,
        idempotency_key: str,
        customer_uid: str,
        customer_email: str,
        metadata: Dict[str, Any],
    ) -> OrderResult:
        """Create a payment order/session for checkout."""
        pass

    @abstractmethod
    async def get_order_status(self, order_id: str) -> OrderStatus:
        """Fetch status of an order."""
        pass

    @abstractmethod
    async def create_refund(
        self,
        order_id: str,
        amount_paise: int,
        refund_id: str,
        reason: str,
    ) -> RefundResult:
        """Create a refund to original payment method."""
        pass

    @abstractmethod
    def validate_webhook_signature(
        self,
        raw_body: bytes,
        headers: Dict[str, str],
    ) -> bool:
        """Verify the cryptographic signature of an incoming webhook."""
        pass

    @abstractmethod
    def parse_webhook_event(self, raw_body: bytes) -> WebhookEvent:
        """Parse validated webhook payload into normalized WebhookEvent."""
        pass
