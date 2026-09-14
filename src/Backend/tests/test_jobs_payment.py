# src/Backend/tests/test_jobs_payment.py

import pytest
from lib.services.wallet import WalletService
from lib.core.monitor import JobManager
from lib.core.job import MonitorJob

manager = JobManager()

@pytest.mark.asyncio
async def test_job_create_wallet_payment(async_client, monkeypatch):
    uid = "test-user-uid-123"
    # Credit ₹10 to user wallet (1000 paise)
    WalletService.credit(
        uid=uid,
        amount_paise=1000,
        txn_type="WALLET_TOPUP",
        description="Topup for job test",
        idempotency_key="key_job_test_1"
    )

    bal_before = WalletService.get_balance(uid)

    payload = {
        "service_provider": "BookMyShow",
        "notification_medium": "SMS",
        "notification_config": {"phone_number": "+919876543210"},
        "phone_number": "+919876543210",
        "sms_consent": True,
        "payment_method": "wallet",
        "check_interval": 60,
        "params": {
            "url": "https://in.bookmyshow.com/movies/chennai/the-odyssey/buytickets/ET00480917/20260730",
            "date_str": "20260730",
            "theatres": ["PVR Grand Mall"]
        }
    }

    res = await async_client.post("/api/jobs", json=payload)
    assert res.status_code == 200
    data = res.json()
    job_id = data["id"]
    price_paise = data["price_paise"]
    assert price_paise > 0
    assert data["payment_method"] == "wallet"

    # Wallet should have been debited by price_paise
    bal_after = WalletService.get_balance(uid)
    assert bal_after == bal_before - price_paise

    # Clean up job
    manager.delete_job(job_id)

@pytest.mark.asyncio
async def test_job_create_insufficient_wallet(async_client):
    uid = "test-user-uid-poor"
    # Poor user with 0 balance
    assert WalletService.get_balance(uid) == 0

    from lib.core.auth import get_authorized_user, get_current_user_claims
    from main import app
    poor_claims = {"uid": uid, "email": "poor@example.com", "authorized": True, "role": "user"}
    app.dependency_overrides[get_authorized_user] = lambda: poor_claims
    app.dependency_overrides[get_current_user_claims] = lambda: poor_claims

    payload = {
        "service_provider": "BookMyShow",
        "notification_medium": "WhatsApp",
        "notification_config": {"phone_number": "+919876543210"},
        "phone_number": "+919876543210",
        "whatsapp_consent": True,
        "payment_method": "wallet",
        "check_interval": 60,
        "params": {
            "url": "https://in.bookmyshow.com/movies/chennai/the-odyssey/buytickets/ET00480917/20260730",
            "date_str": "20260730",
            "theatres": ["PVR Grand Mall"]
        }
    }

    res = await async_client.post("/api/jobs", json=payload)
    assert res.status_code == 402
    assert "Insufficient wallet balance" in res.json().get("detail", "")

@pytest.mark.asyncio
async def test_job_cancel_before_notify_refund(async_client):
    uid = "test-user-uid-123"
    WalletService.credit(
        uid=uid,
        amount_paise=500,
        txn_type="WALLET_TOPUP",
        description="Topup",
        idempotency_key="key_cancel_test_topup"
    )

    bal_before = WalletService.get_balance(uid)

    payload = {
        "service_provider": "BookMyShow",
        "notification_medium": "SMS",
        "notification_config": {"phone_number": "+919876543210"},
        "phone_number": "+919876543210",
        "sms_consent": True,
        "payment_method": "wallet",
        "check_interval": 60,
        "params": {
            "url": "https://in.bookmyshow.com/movies/chennai/the-odyssey/buytickets/ET00480917/20260730",
            "date_str": "20260730",
            "theatres": ["PVR Grand Mall"]
        }
    }

    res = await async_client.post("/api/jobs", json=payload)
    job_id = res.json()["id"]

    # Delete job before notification sent
    del_res = await async_client.delete(f"/api/jobs/{job_id}")
    assert del_res.status_code == 200

    # Wallet should be refunded back to bal_before!
    bal_after_cancel = WalletService.get_balance(uid)
    assert bal_after_cancel == bal_before

@pytest.mark.asyncio
async def test_job_cancel_after_notify_no_refund(async_client):
    uid = "test-user-uid-123"
    WalletService.credit(
        uid=uid,
        amount_paise=500,
        txn_type="WALLET_TOPUP",
        description="Topup",
        idempotency_key="key_cancel_after_notify"
    )

    payload = {
        "service_provider": "BookMyShow",
        "notification_medium": "SMS",
        "notification_config": {"phone_number": "+919876543210"},
        "phone_number": "+919876543210",
        "sms_consent": True,
        "payment_method": "wallet",
        "check_interval": 60,
        "params": {
            "url": "https://in.bookmyshow.com/movies/chennai/the-odyssey/buytickets/ET00480917/20260730",
            "date_str": "20260730",
            "theatres": ["PVR Grand Mall"]
        }
    }

    res = await async_client.post("/api/jobs", json=payload)
    job_id = res.json()["id"]

    # Simulate notification delivered
    job = manager.get_job(job_id)
    job.notification_sent = True
    job.notification_status = "delivered"

    bal_before_del = WalletService.get_balance(uid)

    del_res = await async_client.delete(f"/api/jobs/{job_id}")
    assert del_res.status_code == 200

    # No refund after notification has been sent!
    assert WalletService.get_balance(uid) == bal_before_del

@pytest.mark.asyncio
async def test_job_price_locked_at_creation(async_client):
    from lib.services.pricing import PricingService
    uid = "test-user-uid-123"
    WalletService.credit(
        uid=uid,
        amount_paise=500,
        txn_type="WALLET_TOPUP",
        description="Topup for price lock test",
        idempotency_key="key_price_lock_1"
    )

    payload = {
        "service_provider": "BookMyShow",
        "notification_medium": "SMS",
        "notification_config": {"phone_number": "+919876543210"},
        "phone_number": "+919876543210",
        "sms_consent": True,
        "payment_method": "wallet",
        "check_interval": 60,
        "params": {
            "url": "https://in.bookmyshow.com/movies/chennai/the-odyssey/buytickets/ET00480917/20260730",
            "date_str": "20260730",
            "theatres": ["PVR Grand Mall"]
        }
    }

    res = await async_client.post("/api/jobs", json=payload)
    assert res.status_code == 200
    job_id = res.json()["id"]
    original_price = res.json()["price_paise"]
    assert original_price == 50

    # Admin changes SMS price to 200 paise
    PricingService.update_prices(
        admin_uid="test-admin-uid-999",
        admin_email="admin@example.com",
        sms_paise=200,
        whatsapp_paise=100,
        phone_call_paise=150,
        note="Increase SMS price"
    )

    # Verify existing job price in db remains locked at 50 paise
    job = manager.get_job(job_id)
    assert job.price_paise == 50
    manager.delete_job(job_id)

