# src/Backend/lib/providers/payment/cashfree_gateway.py

import base64
import hashlib
import hmac
import json
import logging
from typing import Dict, Any, Optional
import httpx

from .base import PaymentGateway, OrderStatus, OrderResult, RefundResult, WebhookEvent
from ...utils.redact import redact_email

logger = logging.getLogger("ticketradar.providers.cashfree")

class CashfreePaymentGateway(PaymentGateway):
    """
    Concrete adapter for Cashfree Payment Gateway (v2023-08-01 API).
    Supports sandbox and production environments.
    """

    def __init__(
        self,
        app_id: str,
        secret_key: str,
        webhook_secret: str,
        environment: str = "sandbox",
    ):
        self._app_id = app_id.strip() if app_id else ""
        self._secret_key = secret_key.strip() if secret_key else ""
        self._webhook_secret = webhook_secret.strip() if webhook_secret else self._secret_key
        self._env = (environment or "sandbox").strip().lower()

        if self._env == "production":
            self._base_url = "https://api.cashfree.com/pg"
        else:
            self._base_url = "https://sandbox.cashfree.com/pg"

    def _get_headers(self) -> Dict[str, str]:
        if not self._app_id or not self._secret_key:
            raise ValueError("Cashfree credentials not configured (CASHFREE_APP_ID or CASHFREE_SECRET_KEY missing).")
        return {
            "x-client-id": self._app_id,
            "x-client-secret": self._secret_key,
            "x-api-version": "2023-08-01",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

    async def create_order(
        self,
        amount_paise: int,
        idempotency_key: str,
        customer_uid: str,
        customer_email: str,
        metadata: Dict[str, Any],
    ) -> OrderResult:
        import os
        if (os.getenv("ENVIRONMENT") or "").strip().lower() == "test":
            return OrderResult(
                order_id=idempotency_key,
                session_token=f"mock_session_{idempotency_key}",
                checkout_url=f"https://sandbox.cashfree.com/pg/checkout?order_id={idempotency_key}",
            )

        amount_inr = round(amount_paise / 100.0, 2)
        payload = {
            "order_id": idempotency_key,
            "order_amount": amount_inr,
            "order_currency": "INR",
            "customer_details": {
                "customer_id": customer_uid[:50],
                "customer_email": customer_email,
                "customer_phone": metadata.get("customer_phone", "9999999999")[-10:],
            },
            "order_meta": {
                "return_url": metadata.get("return_url", ""),
                "notify_url": metadata.get("notify_url", ""),
            },
            "order_tags": {
                "type": metadata.get("type", "PAYMENT"),
                "uid": customer_uid[:50],
                "job_id": metadata.get("job_id", "")[:50],
            },
        }

        headers = self._get_headers()
        url = f"{self._base_url}/orders"

        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.post(url, headers=headers, json=payload)
            if resp.status_code not in (200, 201):
                err_text = resp.text
                logger.error(f"Cashfree create_order failed ({resp.status_code}): {err_text}")
                raise RuntimeError(f"Cashfree order creation failed: {resp.status_code} - {err_text}")

            data = resp.json()
            order_id = data.get("order_id", idempotency_key)
            session_token = data.get("payment_session_id", "")
            return OrderResult(
                order_id=order_id,
                session_token=session_token,
                checkout_url=data.get("payments", {}).get("url") or None,
            )

    async def get_order_status(self, order_id: str) -> OrderStatus:
        import os
        if (os.getenv("ENVIRONMENT") or "").strip().lower() == "test":
            return OrderStatus.SUCCESS

        headers = self._get_headers()
        url = f"{self._base_url}/orders/{order_id}"

        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(url, headers=headers)
            if resp.status_code != 200:
                logger.error(f"Cashfree get_order_status failed ({resp.status_code}): {resp.text}")
                return OrderStatus.FAILED

            data = resp.json()
            cf_status = data.get("order_status", "").upper()
            if cf_status == "PAID":
                return OrderStatus.SUCCESS
            elif cf_status in ("ACTIVE", "READY"):
                return OrderStatus.PENDING
            elif cf_status == "EXPIRED":
                return OrderStatus.EXPIRED
            else:
                return OrderStatus.FAILED

    async def create_refund(
        self,
        order_id: str,
        amount_paise: int,
        refund_id: str,
        reason: str,
    ) -> RefundResult:
        import os
        if (os.getenv("ENVIRONMENT") or "").strip().lower() == "test":
            return RefundResult(
                success=True,
                refund_id=refund_id,
                provider_refund_id=f"cf_ref_mock_{refund_id}",
            )

        headers = self._get_headers()
        url = f"{self._base_url}/orders/{order_id}/refunds"
        amount_inr = round(amount_paise / 100.0, 2)

        payload = {
            "refund_amount": amount_inr,
            "refund_id": refund_id,
            "refund_note": reason[:100],
            "refund_speed": "STANDARD",
        }

        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                resp = await client.post(url, headers=headers, json=payload)
                if resp.status_code not in (200, 201):
                    err_text = resp.text
                    logger.error(f"Cashfree refund failed ({resp.status_code}): {err_text}")
                    return RefundResult(
                        success=False,
                        refund_id=refund_id,
                        error_message=f"Cashfree error ({resp.status_code}): {err_text}",
                    )

                data = resp.json()
                cf_refund_id = str(data.get("cf_refund_id", ""))
                return RefundResult(
                    success=True,
                    refund_id=refund_id,
                    provider_refund_id=cf_refund_id,
                )
        except Exception as e:
            logger.error(f"Cashfree refund exception: {e}")
            return RefundResult(
                success=False,
                refund_id=refund_id,
                error_message=str(e),
            )

    def validate_webhook_signature(
        self,
        raw_body: bytes,
        headers: Dict[str, str],
    ) -> bool:
        """
        Validates Cashfree webhook signature.
        Formula: HMAC-SHA256 of (timestamp + raw_body) using webhook_secret.
        Base64-encoded digest compared to x-webhook-signature.
        """
        secret = self._webhook_secret or self._secret_key
        if not secret:
            return False

        # Check case-insensitively for headers
        timestamp = ""
        signature = ""
        for k, v in headers.items():
            k_lower = k.lower()
            if k_lower == "x-webhook-timestamp":
                timestamp = v
            elif k_lower == "x-webhook-signature":
                signature = v

        if not timestamp or not signature:
            return False

        try:
            payload_to_sign = timestamp.encode("utf-8") + raw_body
            computed_hmac = hmac.new(
                secret.encode("utf-8"),
                payload_to_sign,
                hashlib.sha256
            ).digest()
            computed_signature = base64.b64encode(computed_hmac).decode("utf-8")

            return hmac.compare_digest(computed_signature, signature)
        except Exception as e:
            logger.error(f"Error computing Cashfree webhook signature: {e}")
            return False

    def parse_webhook_event(self, raw_body: bytes) -> WebhookEvent:
        """Parse raw Cashfree webhook payload into standardized WebhookEvent."""
        payload = json.loads(raw_body.decode("utf-8"))
        event_type = payload.get("type", "")
        data = payload.get("data", {})
        order = data.get("order", {})
        payment = data.get("payment", {})
        refund = data.get("refund", {})

        order_id = order.get("order_id", "")
        payment_id = payment.get("cf_payment_id")
        if payment_id:
            payment_id = str(payment_id)

        refund_id = refund.get("cf_refund_id") or refund.get("refund_id")
        if refund_id:
            refund_id = str(refund_id)

        raw_amount = payment.get("payment_amount") or order.get("order_amount") or refund.get("refund_amount") or 0.0
        amount_paise = int(round(float(raw_amount) * 100))

        return WebhookEvent(
            event_type=event_type,
            order_id=order_id,
            payment_id=payment_id,
            refund_id=refund_id,
            amount_paise=amount_paise,
            raw=payload,
        )
