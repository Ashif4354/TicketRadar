# src/Backend/tests/test_provider_adapters.py

import pytest
import hmac
import hashlib
import base64
from unittest.mock import MagicMock, AsyncMock, patch

from lib.providers.notification.factory import NotificationProviderFactory
from lib.providers.notification.twilio_adapter import TwilioProviderAdapter
from lib.providers.payment.factory import PaymentGatewayFactory
from lib.providers.payment.cashfree_gateway import CashfreePaymentGateway

def test_notification_provider_factory():
    adapter = NotificationProviderFactory.create()
    assert isinstance(adapter, TwilioProviderAdapter)

def test_notification_provider_factory_unknown(monkeypatch):
    from lib.utils import config
    monkeypatch.setattr(config.settings, "notification_provider", "unknown_provider")
    with pytest.raises(ValueError, match="Unknown notification provider"):
        NotificationProviderFactory.create()

def test_payment_gateway_factory():
    gateway = PaymentGatewayFactory.create()
    assert isinstance(gateway, CashfreePaymentGateway)

def test_payment_gateway_factory_unknown(monkeypatch):
    from lib.utils import config
    monkeypatch.setattr(config.settings, "payment_gateway", "unknown_gateway")
    with pytest.raises(ValueError, match="Unknown payment gateway"):
        PaymentGatewayFactory.create()

def test_cashfree_webhook_signature_validation():
    secret = "my_webhook_secret_123"
    gateway = CashfreePaymentGateway(
        app_id="app_id",
        secret_key="secret",
        webhook_secret=secret,
        environment="sandbox"
    )

    body = b'{"type":"PAYMENT_SUCCESS_WEBHOOK","data":{"order":{"order_id":"ord_1"}}}'
    timestamp = "1672531199000"

    payload_to_sign = timestamp.encode("utf-8") + body
    sig_bytes = hmac.new(secret.encode("utf-8"), payload_to_sign, hashlib.sha256).digest()
    valid_sig = base64.b64encode(sig_bytes).decode("utf-8")

    headers_valid = {
        "x-webhook-timestamp": timestamp,
        "x-webhook-signature": valid_sig,
    }
    assert gateway.validate_webhook_signature(body, headers_valid) is True

    headers_invalid = {
        "x-webhook-timestamp": timestamp,
        "x-webhook-signature": "wrong_signature",
    }
    assert gateway.validate_webhook_signature(body, headers_invalid) is False

def test_cashfree_parse_webhook_event():
    gateway = CashfreePaymentGateway("app", "sec", "webhook_sec", "sandbox")
    body = b'''{
        "type": "PAYMENT_SUCCESS_WEBHOOK",
        "data": {
            "order": {"order_id": "test_order_123", "order_amount": 15.50},
            "payment": {"cf_payment_id": 999888, "payment_amount": 15.50}
        }
    }'''
    event = gateway.parse_webhook_event(body)
    assert event.event_type == "PAYMENT_SUCCESS_WEBHOOK"
    assert event.order_id == "test_order_123"
    assert event.payment_id == "999888"
    assert event.amount_paise == 1550

def test_twilio_adapter_validate_signature_valid():
    from twilio.request_validator import RequestValidator
    auth_token = "1234567890abcdef1234567890abcdef"
    adapter = TwilioProviderAdapter(
        account_sid="AC123",
        auth_token=auth_token,
        from_number="+919876543210"
    )
    url = "https://example.com/api/twilio/message-status"
    params = {"MessageSid": "SM123", "MessageStatus": "delivered"}
    validator = RequestValidator(auth_token)
    valid_sig = validator.compute_signature(url, params)

    body = b"MessageSid=SM123&MessageStatus=delivered"
    headers = {"X-Twilio-Signature": valid_sig}
    assert adapter.validate_incoming_webhook(body, headers, url) is True

def test_twilio_adapter_validate_signature_invalid():
    auth_token = "1234567890abcdef1234567890abcdef"
    adapter = TwilioProviderAdapter(
        account_sid="AC123",
        auth_token=auth_token,
        from_number="+919876543210"
    )
    url = "https://example.com/api/twilio/message-status"
    body = b"MessageSid=SM123&MessageStatus=delivered"
    headers = {"X-Twilio-Signature": "invalid_signature"}
    assert adapter.validate_incoming_webhook(body, headers, url) is False


@pytest.mark.asyncio
async def test_twilio_adapter_test_environment_no_network_calls():
    adapter = TwilioProviderAdapter(
        account_sid="ACmockaccountsid0000000000000000",
        auth_token="mockauthtoken00000000000000000",
        from_number="+919876543210"
    )

    sms_res = await adapter.send_sms("+919876543210", "Hello", idempotency_key="sms_test_1")
    assert sms_res.success is True
    assert "SM_mock_sms_test_1" in sms_res.provider_id

    wa_res = await adapter.send_whatsapp_template("+919876543210", "HX123", {"1": "Movie"}, idempotency_key="wa_test_1")
    assert wa_res.success is True
    assert "WA_mock_wa_test_1" in wa_res.provider_id

    call_res = await adapter.initiate_call("+919876543210", "http://twiml", "http://status", idempotency_key="call_test_1")
    assert call_res.success is True
    assert "CA_mock_call_test_1" in call_res.call_id


@pytest.mark.asyncio
async def test_cashfree_gateway_test_environment_no_network_calls():
    gateway = CashfreePaymentGateway(
        app_id="mock_app_id",
        secret_key="mock_secret",
        webhook_secret="mock_webhook_secret",
        environment="sandbox"
    )

    order_res = await gateway.create_order(
        amount_paise=1000,
        idempotency_key="order_test_1",
        customer_uid="user1",
        customer_email="user@test.com",
        metadata={}
    )
    assert order_res.order_id == "order_test_1"
    assert "mock_session_order_test_1" in order_res.session_token

    from lib.providers.payment.base import OrderStatus
    status = await gateway.get_order_status("order_test_1")
    assert status == OrderStatus.SUCCESS

    refund_res = await gateway.create_refund(
        order_id="order_test_1",
        amount_paise=1000,
        refund_id="refund_test_1",
        reason="Test refund"
    )
    assert refund_res.success is True
    assert "cf_ref_mock_refund_test_1" in refund_res.provider_refund_id

