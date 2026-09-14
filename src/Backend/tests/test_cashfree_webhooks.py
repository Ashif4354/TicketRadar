# src/Backend/tests/test_cashfree_webhooks.py

import pytest
import hmac
import hashlib
import base64
import json
from unittest.mock import patch

from lib.services.wallet import WalletService
from lib.core import auth

@pytest.mark.asyncio
async def test_cashfree_payment_success_credits_wallet(async_client):
    order_id = "test_order_topup_99"
    amount_paise = 20000  # ₹200.00
    uid = "test-user-uid-123"

    # Pre-populate payment doc
    auth.db.collection("payments").document("pay_99").set({
        "id": "pay_99",
        "uid": uid,
        "type": "WALLET_TOPUP",
        "amount_paise": amount_paise,
        "status": "pending",
        "gateway_order_id": order_id,
    })

    payload = {
        "type": "PAYMENT_SUCCESS_WEBHOOK",
        "data": {
            "order": {"order_id": order_id, "order_amount": 200.0},
            "payment": {"cf_payment_id": "cf_pay_123", "payment_amount": 200.0}
        }
    }
    raw_body = json.dumps(payload).encode("utf-8")

    # Generate valid signature
    secret = "mock_webhook_secret"
    timestamp = "1672531199000"
    payload_to_sign = timestamp.encode("utf-8") + raw_body
    sig = base64.b64encode(hmac.new(secret.encode("utf-8"), payload_to_sign, hashlib.sha256).digest()).decode("utf-8")

    headers = {
        "x-webhook-timestamp": timestamp,
        "x-webhook-signature": sig,
        "Content-Type": "application/json"
    }

    res = await async_client.post("/api/cashfree/webhook", content=raw_body, headers=headers)
    assert res.status_code == 200

    # Verify wallet was credited
    assert WalletService.get_balance(uid) == 20000

@pytest.mark.asyncio
async def test_cashfree_duplicate_webhook_no_double_credit(async_client):
    order_id = "test_order_dup_88"
    amount_paise = 5000  # ₹50.00
    uid = "test-user-uid-123"

    auth.db.collection("payments").document("pay_88").set({
        "id": "pay_88",
        "uid": uid,
        "type": "WALLET_TOPUP",
        "amount_paise": amount_paise,
        "status": "pending",
        "gateway_order_id": order_id,
    })

    payload = {
        "type": "PAYMENT_SUCCESS_WEBHOOK",
        "data": {
            "order": {"order_id": order_id, "order_amount": 50.0},
            "payment": {"cf_payment_id": "cf_pay_888", "payment_amount": 50.0}
        }
    }
    raw_body = json.dumps(payload).encode("utf-8")
    secret = "mock_webhook_secret"
    timestamp = "1672531199000"
    sig = base64.b64encode(hmac.new(secret.encode("utf-8"), timestamp.encode("utf-8") + raw_body, hashlib.sha256).digest()).decode("utf-8")

    headers = {
        "x-webhook-timestamp": timestamp,
        "x-webhook-signature": sig,
        "Content-Type": "application/json"
    }

    # Initial balance
    initial_bal = WalletService.get_balance(uid)

    # First call
    res1 = await async_client.post("/api/cashfree/webhook", content=raw_body, headers=headers)
    assert res1.status_code == 200
    assert WalletService.get_balance(uid) == initial_bal + 5000

    # Duplicate call
    res2 = await async_client.post("/api/cashfree/webhook", content=raw_body, headers=headers)
    assert res2.status_code == 200
    assert res2.json().get("status") == "already_processed"

    # Balance must remain exactly initial + 5000
    assert WalletService.get_balance(uid) == initial_bal + 5000

@pytest.mark.asyncio
async def test_cashfree_invalid_signature_rejected(async_client, monkeypatch):
    import os
    monkeypatch.setenv("DISABLE_SECURITY", "false")
    from lib.utils import config
    monkeypatch.setattr(config.settings, "disable_security", False)

    body = b'{"type":"PAYMENT_SUCCESS_WEBHOOK","data":{}}'
    headers = {
        "x-webhook-timestamp": "1672531199000",
        "x-webhook-signature": "bogus_signature",
        "Content-Type": "application/json"
    }
    res = await async_client.post("/api/cashfree/webhook", content=body, headers=headers)
    assert res.status_code == 403
