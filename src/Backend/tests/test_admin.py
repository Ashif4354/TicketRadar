# src/Backend/tests/test_admin.py

import pytest
from unittest.mock import patch, AsyncMock
from lib.services.wallet import WalletService
from lib.providers.payment.base import RefundResult

@pytest.mark.asyncio
async def test_admin_pricing_endpoints(admin_async_client):
    # 1. Get pricing
    res = await admin_async_client.get("/admin/pricing")
    assert res.status_code == 200
    assert "current" in res.json()

    # 2. Update pricing
    update_payload = {
        "sms_paise": 65,
        "whatsapp_paise": 115,
        "phone_call_paise": 180,
        "note": "Quarterly review price change"
    }
    res_up = await admin_async_client.post("/admin/pricing", json=update_payload)
    assert res_up.status_code == 200
    assert res_up.json()["config"]["sms_paise"] == 65

@pytest.mark.asyncio
async def test_admin_wallet_adjust_and_logs(admin_async_client):
    target_uid = "target-user-007"
    assert WalletService.get_balance(target_uid) == 0

    # Credit ₹5 (500 paise)
    res_credit = await admin_async_client.post(
        f"/admin/wallets/{target_uid}/adjust",
        json={"amount_paise": 500, "direction": "CREDIT", "reason": "Customer loyalty bonus"}
    )
    assert res_credit.status_code == 200
    assert WalletService.get_balance(target_uid) == 500

    # Get user wallet
    res_w = await admin_async_client.get(f"/admin/wallets/{target_uid}")
    assert res_w.status_code == 200
    assert res_w.json()["balance_paise"] == 500

    # Debit ₹2 (200 paise)
    res_debit = await admin_async_client.post(
        f"/admin/wallets/{target_uid}/adjust",
        json={"amount_paise": 200, "direction": "DEBIT", "reason": "Manual correction"}
    )
    assert res_debit.status_code == 200
    assert WalletService.get_balance(target_uid) == 300

    # Check audit logs
    res_logs = await admin_async_client.get("/admin/audit-logs")
    assert res_logs.status_code == 200

@pytest.mark.asyncio
async def test_admin_cashfree_refund(admin_async_client, monkeypatch):
    with patch("lib.providers.payment.cashfree_gateway.CashfreePaymentGateway.create_refund", new_callable=AsyncMock) as mock_refund:
        mock_refund.return_value = RefundResult(
            success=True,
            refund_id="ref123",
            provider_refund_id="cf_ref_999",
            error_message=None
        )

        payload = {
            "order_id": "ord_cf_123",
            "amount_paise": 1000,
            "reason": "Customer request refund"
        }
        res = await admin_async_client.post("/admin/refunds/cashfree", json=payload)
        assert res.status_code == 200
        assert res.json()["success"] is True
        assert res.json()["provider_refund_id"] == "cf_ref_999"
