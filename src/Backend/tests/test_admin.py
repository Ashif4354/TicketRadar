import pytest
from unittest.mock import patch, AsyncMock
from httpx import AsyncClient, ASGITransport
from main import app
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

@pytest.mark.asyncio
async def test_admin_gateway_refund(admin_async_client, monkeypatch):
    with patch("lib.providers.payment.cashfree_gateway.CashfreePaymentGateway.create_refund", new_callable=AsyncMock) as mock_refund:
        mock_refund.return_value = RefundResult(
            success=True,
            refund_id="ref_gw_123",
            provider_refund_id="gw_ref_888",
            error_message=None
        )

        payload = {
            "order_id": "ord_gw_123",
            "amount_paise": 1500,
            "reason": "Administrative gateway refund"
        }
        res = await admin_async_client.post("/admin/refunds/gateway", json=payload)
        assert res.status_code == 200
        assert res.json()["success"] is True
        assert res.json()["provider_refund_id"] == "gw_ref_888"


@pytest.mark.asyncio
async def test_admin_disabled_when_security_disabled(monkeypatch):
    """When DISABLE_SECURITY is true, all admin panel endpoints must return 403."""
    monkeypatch.setenv("DISABLE_SECURITY", "true")
    from lib.utils.config import settings
    if settings:
        monkeypatch.setattr(settings, "disable_security", True)

    app.dependency_overrides.clear()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        get_paths = [
            "/admin/counts",
            "/admin/users",
            "/admin/requests",
            "/admin/pricing",
            "/admin/wallets/user1",
            "/admin/audit-logs",
        ]
        for path in get_paths:
            res = await client.get(path)
            assert res.status_code == 403
            assert res.json()["detail"] == "Admin panel is disabled because DISABLE_SECURITY is true"

            # Rejection holds even if an Authorization header is provided
            res_auth = await client.get(path, headers={"Authorization": "Bearer any-token"})
            assert res_auth.status_code == 403
            assert res_auth.json()["detail"] == "Admin panel is disabled because DISABLE_SECURITY is true"

        post_endpoints = [
            ("/admin/pricing", {"sms_paise": 50}),
            ("/admin/requests/req-01/approve", {}),
            ("/admin/requests/req-01/deny", {}),
            ("/admin/users/user1/block", {}),
            ("/admin/users/user1/unblock", {}),
            ("/admin/users/user1/role", {"role": "admin"}),
            ("/admin/wallets/user1/adjust", {"amount_paise": 100, "direction": "CREDIT", "reason": "test"}),
            ("/admin/refunds/cashfree", {"order_id": "ord1", "amount_paise": 100, "reason": "test"}),
        ]
        for endpoint, payload in post_endpoints:
            res_post = await client.post(endpoint, json=payload)
            assert res_post.status_code == 403
            assert res_post.json()["detail"] == "Admin panel is disabled because DISABLE_SECURITY is true"


@pytest.mark.asyncio
async def test_admin_transactions_and_email_discord_pricing(admin_async_client):
    # 1. Update pricing with email and discord paise
    update_payload = {
        "sms_paise": 55,
        "whatsapp_paise": 105,
        "phone_call_paise": 155,
        "email_paise": 10,
        "discord_paise": 5,
        "note": "Pricing with email and discord"
    }
    res_up = await admin_async_client.post("/admin/pricing", json=update_payload)
    assert res_up.status_code == 200
    cfg = res_up.json()["config"]
    assert cfg["email_paise"] == 10
    assert cfg["discord_paise"] == 5

    # 2. Get global transactions
    res_txns = await admin_async_client.get("/admin/transactions?page=1&page_size=10")
    assert res_txns.status_code == 200
    data = res_txns.json()
    assert "items" in data
    assert "total" in data
    assert "page" in data


@pytest.mark.asyncio
async def test_admin_start_job_free_of_charge(admin_async_client):
    from lib.core.job import MonitorJob
    from lib.services.wallet import WalletService
    from main import manager

    user_uid = "job-owner-user-999"
    # User has 1000 paise in wallet
    WalletService.credit(user_uid, 1000, "TOPUP", "Initial balance", "init_key_999")
    initial_balance = WalletService.get_balance(user_uid)
    assert initial_balance == 1000

    test_job = MonitorJob(
        params={"movie_url": "https://in.bookmyshow.com/movies/test/123", "theatres": ["PVR"], "date_str": "20261001"},
        notification_medium="Email",
        notification_config={"recipient_email": "user@example.com"},
        created_by=user_uid,
        creator_email="user@example.com"
    )
    test_job.status = "Stopped"
    manager.jobs[test_job.id] = test_job

    # Admin starts the job
    res_start = await admin_async_client.post(f"/admin/jobs/{test_job.id}/start")
    assert res_start.status_code == 200
    assert res_start.json()["success"] is True
    assert test_job.status == "Running"

    # CRITICAL: Verify the user was NOT charged at all
    assert WalletService.get_balance(user_uid) == initial_balance

    # Calling start again when already running
    res_again = await admin_async_client.post(f"/admin/jobs/{test_job.id}/start")
    assert res_again.status_code == 200
    assert "already running" in res_again.json()["message"]

    # Clean up
    manager.stop_job(test_job.id)
    if test_job.id in manager.jobs:
        del manager.jobs[test_job.id]


