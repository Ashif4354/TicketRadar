# src/Backend/tests/test_wallet.py

import pytest
from lib.services.wallet import WalletService, InsufficientFundsError

def test_wallet_initial_balance_is_zero():
    balance = WalletService.get_balance("user-zero-balance")
    assert balance == 0

def test_wallet_credit_and_debit_cycle():
    uid = "user-cycle-test"

    # 1. Credit 500 paise (₹5.00)
    res_credit = WalletService.credit(
        uid=uid,
        amount_paise=500,
        txn_type="WALLET_TOPUP",
        description="Top-up test",
        idempotency_key="key_topup_1"
    )
    assert res_credit["direction"] == "CREDIT"
    assert res_credit["amount_paise"] == 500
    assert res_credit["balance_after_paise"] == 500

    assert WalletService.get_balance(uid) == 500

    # 2. Debit 150 paise (₹1.50)
    res_debit = WalletService.debit(
        uid=uid,
        amount_paise=150,
        txn_type="JOB_PAYMENT",
        description="Job payment test",
        idempotency_key="key_debit_1",
        job_id="job001"
    )
    assert res_debit["direction"] == "DEBIT"
    assert res_debit["amount_paise"] == 150
    assert res_debit["balance_after_paise"] == 350

    assert WalletService.get_balance(uid) == 350

def test_wallet_debit_insufficient_funds():
    uid = "user-insufficient"
    WalletService.credit(
        uid=uid,
        amount_paise=100,
        txn_type="WALLET_TOPUP",
        description="Small topup",
        idempotency_key="key_small_1"
    )

    with pytest.raises(InsufficientFundsError):
        WalletService.debit(
            uid=uid,
            amount_paise=200,  # exceeds balance of 100
            txn_type="JOB_PAYMENT",
            description="Exceeding debit",
            idempotency_key="key_fail_1"
        )

    # Balance remains 100
    assert WalletService.get_balance(uid) == 100

def test_wallet_idempotency_replay():
    uid = "user-idempotency"
    # First credit
    res1 = WalletService.credit(
        uid=uid,
        amount_paise=250,
        txn_type="WALLET_TOPUP",
        description="Idempotent credit",
        idempotency_key="unique_idemp_key_123"
    )
    assert res1["balance_after_paise"] == 250

    # Second credit with SAME idempotency key
    res2 = WalletService.credit(
        uid=uid,
        amount_paise=250,
        txn_type="WALLET_TOPUP",
        description="Idempotent credit repeat",
        idempotency_key="unique_idemp_key_123"
    )

    # Must return same record, no double-credit
    assert res2["id"] == res1["id"]
    assert WalletService.get_balance(uid) == 250


@pytest.mark.asyncio
async def test_wallet_topup_initiate_dynamic_gateway(async_client, monkeypatch):
    from unittest.mock import AsyncMock, patch
    from lib.providers.payment.base import OrderResult
    from lib.core import auth
    from lib.utils.config import settings

    if settings:
        monkeypatch.setattr(settings, "payment_gateway", "cashfree")

    with patch("lib.providers.payment.cashfree_gateway.CashfreePaymentGateway.create_order", new_callable=AsyncMock) as mock_create:
        mock_create.return_value = OrderResult(
            order_id="order_123",
            session_token="sess_123",
            checkout_url="https://checkout.example.com",
        )
        res = await async_client.post("/api/wallet/topup/initiate", json={"amount_paise": 500})
        assert res.status_code == 200
        data = res.json()
        assert data["order_id"] == "order_123"
        assert data["session_token"] == "sess_123"
        assert data["checkout_url"] == "https://checkout.example.com"

        payment_id = data["payment_id"]
        doc = auth.db.collection("payments").document(payment_id).get()
        assert doc.exists
        pdata = doc.to_dict()
        assert pdata["gateway_name"] == "cashfree"
        assert pdata["payment_method"] == "gateway"

