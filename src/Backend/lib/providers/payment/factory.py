# src/Backend/lib/providers/payment/factory.py

from typing import Dict, Type
from .base import PaymentGateway
from .cashfree_gateway import CashfreePaymentGateway
from ...utils.config import settings

class PaymentGatewayFactory:
    """
    Returns the configured payment gateway instance.
    Provider is selected via PAYMENT_GATEWAY setting/env var (default: 'cashfree').
    """

    _registry: Dict[str, Type[PaymentGateway]] = {
        "cashfree": CashfreePaymentGateway,
    }

    @classmethod
    def register_gateway(cls, name: str, gateway_cls: Type[PaymentGateway]) -> None:
        cls._registry[name.lower()] = gateway_cls

    @classmethod
    def create(cls) -> PaymentGateway:
        gateway_name = (settings.payment_gateway if settings else "cashfree").strip().lower()
        gateway_cls = cls._registry.get(gateway_name)
        if not gateway_cls:
            raise ValueError(f"Unknown payment gateway: {gateway_name}")

        if gateway_cls is CashfreePaymentGateway:
            return CashfreePaymentGateway(
                app_id=settings.cashfree_app_id if settings else "",
                secret_key=settings.cashfree_secret_key if settings else "",
                webhook_secret=settings.cashfree_webhook_secret if settings else "",
                environment=settings.cashfree_environment if settings else "sandbox",
            )

        return gateway_cls()
