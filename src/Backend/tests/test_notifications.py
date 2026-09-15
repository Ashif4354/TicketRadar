# src/Backend/tests/test_notifications.py

import pytest
from unittest.mock import AsyncMock

from lib.utils.phone import normalize_indian_phone, validate_phone
from lib.utils.redact import redact_phone, redact_email
from lib.providers.notification.base import NotificationProviderAdapter, ProviderMessageResult, ProviderCallResult
from lib.services.notification.sms_strategy import SMSNotificationStrategy
from lib.services.notification.whatsapp_strategy import WhatsAppNotificationStrategy
from lib.services.notification.phone_call_strategy import PhoneCallNotificationStrategy
from lib.services.notification.factory import NotificationStrategyFactory

def test_phone_normalization_valid():
    assert normalize_indian_phone("+919876543210") == "+919876543210"
    assert normalize_indian_phone("9876543210") == "+919876543210"
    assert normalize_indian_phone("09876543210") == "+919876543210"
    assert normalize_indian_phone("+91 98765 43210") == "+919876543210"
    assert validate_phone("9876543210") is True

def test_phone_normalization_invalid():
    # Non-Indian number (US number +1)
    with pytest.raises(ValueError):
        normalize_indian_phone("+12025550123")
    # Invalid length
    with pytest.raises(ValueError):
        normalize_indian_phone("12345")
    # Landline or non-mobile starting digit
    with pytest.raises(ValueError):
        normalize_indian_phone("0112345678")
    assert validate_phone("invalid") is False

def test_redact_phone():
    assert redact_phone("+919876543210") == "+91XXXXXX3210"
    assert redact_phone("9876543210") == "XXXXXX3210"
    assert redact_phone(None) == "[EMPTY]"

def test_redact_email():
    assert redact_email("john.doe@example.com") == "j***e@example.com"
    assert redact_email("a@example.com") == "*@example.com"
    assert redact_email(None) == "[EMPTY]"

@pytest.mark.asyncio
async def test_sms_strategy_uses_provider():
    mock_adapter = AsyncMock(spec=NotificationProviderAdapter)
    mock_adapter.send_sms.return_value = ProviderMessageResult(success=True, provider_id="SM_TEST_123")

    strategy = SMSNotificationStrategy(phone_number="+919876543210", provider=mock_adapter, job_id="job123")
    success, msg = await strategy.send_notification(
        subject="Alert",
        movie_name="Kalki 2898 AD",
        date_str="20260719",
        available_theatres=["PVR Velachery"],
        unavailable_theatres=[],
        url="https://in.bookmyshow.com"
    )

    assert success is True
    assert "SM_TEST_123" in msg
    mock_adapter.send_sms.assert_awaited_once()

@pytest.mark.asyncio
async def test_whatsapp_strategy_uses_provider():
    mock_adapter = AsyncMock(spec=NotificationProviderAdapter)
    mock_adapter.send_whatsapp_template.return_value = ProviderMessageResult(success=True, provider_id="WA_TEST_456")

    strategy = WhatsAppNotificationStrategy(
        phone_number="+919876543210",
        provider=mock_adapter,
        content_sid="HX_TEST",
        job_id="job123"
    )
    success, msg = await strategy.send_notification(
        subject="Alert",
        movie_name="Kalki 2898 AD",
        date_str="20260719",
        available_theatres=["PVR Velachery"],
        unavailable_theatres=[],
        url="https://in.bookmyshow.com"
    )

    assert success is True
    assert "WA_TEST_456" in msg
    mock_adapter.send_whatsapp_template.assert_awaited_once()

@pytest.mark.asyncio
async def test_phone_call_strategy_uses_provider():
    mock_adapter = AsyncMock(spec=NotificationProviderAdapter)
    mock_adapter.initiate_call.return_value = ProviderCallResult(success=True, call_id="CA_TEST_789")

    strategy = PhoneCallNotificationStrategy(
        phone_number="+919876543210",
        provider=mock_adapter,
        base_url="http://localhost:8000",
        job_id="job123"
    )
    success, msg = await strategy.send_notification(
        subject="Alert",
        movie_name="Kalki 2898 AD",
        date_str="20260719",
        available_theatres=["PVR Velachery"],
        unavailable_theatres=[],
        url="https://in.bookmyshow.com"
    )

    assert success is True
    assert "CA_TEST_789" in msg
    mock_adapter.initiate_call.assert_awaited_once()

def test_notification_strategy_factory_instantiates_all_mediums():
    mock_adapter = AsyncMock(spec=NotificationProviderAdapter)
    sms = NotificationStrategyFactory.create_strategy("sms", {"phone_number": "+919876543210"}, provider_adapter=mock_adapter)
    assert isinstance(sms, SMSNotificationStrategy)

    wa = NotificationStrategyFactory.create_strategy("whatsapp", {"phone_number": "+919876543210"}, provider_adapter=mock_adapter)
    assert isinstance(wa, WhatsAppNotificationStrategy)

    call = NotificationStrategyFactory.create_strategy("phone_call", {"phone_number": "+919876543210"}, provider_adapter=mock_adapter)
    assert isinstance(call, PhoneCallNotificationStrategy)

@pytest.mark.asyncio
async def test_sms_delivered_marks_sent(async_client):
    from lib.core.monitor import JobManager
    from lib.core.job import MonitorJob
    from lib.core.auth import db

    manager = JobManager()
    job_id = "job-sms-deliv"
    job = MonitorJob(
        job_id=job_id,
        params={
            "url": "https://in.bookmyshow.com",
            "date_str": "20260719",
            "theatres": ["PVR"],
        },
        service_provider="BookMyShow",
        check_interval=60,
        notification_medium="SMS",
        notification_config={"phone_number": "+919876543210"},
        created_by="test-user-uid-123",
        price_paise=50
    )
    job.status = "Running"
    manager.jobs[job_id] = job
    manager._save_job_to_firestore(job)

    # Simulate message status callback
    res = await async_client.post(
        f"/api/twilio/message-status?job_id={job_id}",
        data={"MessageSid": "SM_TEST_DELIV_1", "MessageStatus": "delivered"}
    )
    assert res.status_code == 200
    assert job.notification_status == "delivered"
    assert job.notification_sent is True
    manager.delete_job(job_id)

@pytest.mark.asyncio
async def test_sms_3x_undelivered_refund(async_client):
    from lib.core.monitor import JobManager
    from lib.core.job import MonitorJob
    from lib.services.wallet import WalletService

    uid = "test-user-uid-123"
    manager = JobManager()
    job_id = "job-sms-fail"
    job = MonitorJob(
        job_id=job_id,
        params={
            "url": "https://in.bookmyshow.com",
            "date_str": "20260719",
            "theatres": ["PVR"],
        },
        service_provider="BookMyShow",
        check_interval=60,
        notification_medium="SMS",
        notification_config={"phone_number": "+919876543210"},
        created_by=uid,
        price_paise=50
    )
    job.status = "Running"
    job.notification_attempt_count = 3  # terminal 3rd attempt
    manager.jobs[job_id] = job
    manager._save_job_to_firestore(job)

    bal_before = WalletService.get_balance(uid)

    res = await async_client.post(
        f"/api/twilio/message-status?job_id={job_id}",
        data={"MessageSid": "SM_TEST_FAIL_3", "MessageStatus": "failed"}
    )
    assert res.status_code == 200
    assert job.notification_status == "failed"
    assert job.refund_issued is True
    bal_after = WalletService.get_balance(uid)
    assert bal_after == bal_before + 50
    manager.delete_job(job_id)

@pytest.mark.asyncio
async def test_call_3x_no_answer_policy_exempt(async_client):
    from lib.core.monitor import JobManager
    from lib.core.job import MonitorJob
    from lib.services.wallet import WalletService

    uid = "test-user-uid-123"
    manager = JobManager()
    job_id = "job-call-noans"
    job = MonitorJob(
        job_id=job_id,
        params={
            "url": "https://in.bookmyshow.com",
            "date_str": "20260719",
            "theatres": ["PVR"],
        },
        service_provider="BookMyShow",
        check_interval=60,
        notification_medium="Phone Call",
        notification_config={"phone_number": "+919876543210"},
        created_by=uid,
        price_paise=150
    )
    job.status = "Running"
    job.notification_attempt_count = 3  # 3rd attempt
    manager.jobs[job_id] = job
    manager._save_job_to_firestore(job)

    bal_before = WalletService.get_balance(uid)

    res = await async_client.post(
        f"/api/twilio/call-status?job_id={job_id}",
        data={"CallSid": "CA_TEST_NOANS_3", "CallStatus": "no-answer"}
    )
    assert res.status_code == 200
    # Policy exempt delivery: marked sent, no refund!
    assert job.notification_status == "policy_exempt"
    assert job.notification_sent is True
    assert job.refund_issued is False
    bal_after = WalletService.get_balance(uid)
    assert bal_after == bal_before  # No refund
    manager.delete_job(job_id)

@pytest.mark.asyncio
async def test_call_3x_busy_policy_exempt(async_client):
    from lib.core.monitor import JobManager
    from lib.core.job import MonitorJob
    from lib.services.wallet import WalletService

    uid = "test-user-uid-123"
    manager = JobManager()
    job_id = "job-call-busy"
    job = MonitorJob(
        job_id=job_id,
        params={
            "url": "https://in.bookmyshow.com",
            "date_str": "20260719",
            "theatres": ["PVR"],
        },
        service_provider="BookMyShow",
        check_interval=60,
        notification_medium="Phone Call",
        notification_config={"phone_number": "+919876543210"},
        created_by=uid,
        price_paise=150
    )
    job.status = "Running"
    job.notification_attempt_count = 3
    manager.jobs[job_id] = job
    manager._save_job_to_firestore(job)

    bal_before = WalletService.get_balance(uid)

    res = await async_client.post(
        f"/api/twilio/call-status?job_id={job_id}",
        data={"CallSid": "CA_TEST_BUSY_3", "CallStatus": "busy"}
    )
    assert res.status_code == 200
    assert job.notification_status == "policy_exempt"
    assert job.notification_sent is True
    assert job.refund_issued is False
    assert WalletService.get_balance(uid) == bal_before
    manager.delete_job(job_id)

@pytest.mark.asyncio
async def test_call_technical_failure_refund(async_client):
    from lib.core.monitor import JobManager
    from lib.core.job import MonitorJob
    from lib.services.wallet import WalletService

    uid = "test-user-uid-123"
    manager = JobManager()
    job_id = "job-call-techfail"
    job = MonitorJob(
        job_id=job_id,
        params={
            "url": "https://in.bookmyshow.com",
            "date_str": "20260719",
            "theatres": ["PVR"],
        },
        service_provider="BookMyShow",
        check_interval=60,
        notification_medium="Phone Call",
        notification_config={"phone_number": "+919876543210"},
        created_by=uid,
        price_paise=150
    )
    job.status = "Running"
    job.notification_attempt_count = 3
    manager.jobs[job_id] = job
    manager._save_job_to_firestore(job)

    bal_before = WalletService.get_balance(uid)

    res = await async_client.post(
        f"/api/twilio/call-status?job_id={job_id}",
        data={"CallSid": "CA_TEST_FAILED_3", "CallStatus": "failed"}
    )
    assert res.status_code == 200
    assert job.notification_status == "failed"
    assert job.refund_issued is True
    bal_after = WalletService.get_balance(uid)
    assert bal_after == bal_before + 150
    manager.delete_job(job_id)

@pytest.mark.asyncio
async def test_whatsapp_stop_reply_revokes_consent(async_client):
    from lib.core.auth import db

    uid = "test-user-uid-123"
    phone = "+919876543210"
    db.collection("notification_consents").document(uid).set({
        "uid": uid,
        "phone_number": phone,
        "whatsapp_consented": True,
    })

    res = await async_client.post(
        "/api/twilio/whatsapp-incoming",
        data={"From": f"whatsapp:{phone}", "Body": "STOP"}
    )
    assert res.status_code == 200

    doc = db.collection("notification_consents").document(uid).get()
    assert doc.exists
    assert doc.to_dict()["whatsapp_consented"] is False


@pytest.mark.asyncio
async def test_discord_embed_builder():
    from lib.services.notification.DiscordEmbed import DiscordEmbed

    embed = (
        DiscordEmbed(title="Test Title", description="Test Description", color=0x10B981)
        .add_field("Field 1", "Value 1", inline=True)
        .set_thumbnail("https://example.com/thumb.png")
        .set_footer("Footer text", "https://example.com/icon.png")
    )
    d = embed.to_dict()
    assert d["title"] == "Test Title"
    assert d["description"] == "Test Description"
    assert d["color"] == 0x10B981
    assert len(d["fields"]) == 1
    assert d["fields"][0]["name"] == "Field 1"
    assert d["thumbnail"]["url"] == "https://example.com/thumb.png"
    assert d["footer"]["text"] == "Footer text"

    payload = embed.to_payload()
    assert "embeds" in payload
    assert len(payload["embeds"]) == 1


@pytest.mark.asyncio
async def test_discord_embed_test_env_suppression(monkeypatch):
    from lib.services.notification.DiscordEmbed import DiscordEmbed

    monkeypatch.setenv("ENVIRONMENT", "test")
    success, msg = await DiscordEmbed.send_payload("https://discord.com/api/webhooks/test/123", {"embeds": []})
    assert success is True
    assert "Skipped in test environment" in msg

    # Missing webhook url
    success, msg = await DiscordEmbed.send_payload("", {"embeds": []})
    assert success is False
    assert "missing" in msg.lower()


@pytest.mark.asyncio
async def test_discord_embed_dispatch_success(monkeypatch):
    from unittest.mock import patch, MagicMock
    from lib.services.notification.DiscordEmbed import DiscordEmbed

    monkeypatch.setenv("ENVIRONMENT", "production")

    mock_resp = MagicMock()
    mock_resp.status_code = 204

    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value = mock_resp
        success, msg = await DiscordEmbed.send_embed(
            webhook_url="https://discord.com/api/webhooks/123/abc",
            title="Production Alert",
            description="All systems nominal"
        )
        assert success is True
        assert "successfully" in msg
        mock_post.assert_awaited_once()


@pytest.mark.asyncio
async def test_admin_notifier_uses_discord_embed(monkeypatch):
    from unittest.mock import patch
    from lib.services.notification.admin_notifier import send_admin_discord_embed

    monkeypatch.setattr("lib.services.notification.admin_notifier.settings.admin_discord_webhook_url", "https://discord.com/api/webhooks/123/test")
    with patch("lib.services.notification.DiscordEmbed.DiscordEmbed.send_embed", new_callable=AsyncMock) as mock_send:
        mock_send.return_value = (True, "OK")
        await send_admin_discord_embed(
            title="Test Admin Alert",
            description="Testing discord embed dispatch",
            color=0x7C3AED
        )
        mock_send.assert_awaited_once()


@pytest.mark.asyncio
async def test_test_notification_rejects_paid_mediums_by_default(async_client):
    # SMS (default ₹0.50)
    res = await async_client.post("/api/test-notification", json={
        "medium": "sms",
        "target": "9876543210"
    })
    assert res.status_code == 400
    assert "only allowed for free mediums" in res.json()["detail"]
    assert "paid medium" in res.json()["detail"]

    # WhatsApp (default ₹1.00)
    res = await async_client.post("/api/test-notification", json={
        "medium": "whatsapp",
        "target": "9876543210"
    })
    assert res.status_code == 400
    assert "only allowed for free mediums" in res.json()["detail"]

    # Phone Call (default ₹1.50)
    res = await async_client.post("/api/test-notification", json={
        "medium": "phone_call",
        "target": "9876543210"
    })
    assert res.status_code == 400
    assert "only allowed for free mediums" in res.json()["detail"]


@pytest.mark.asyncio
async def test_test_notification_allows_free_mediums(async_client, monkeypatch):
    from unittest.mock import AsyncMock, MagicMock
    from lib.services.notification.factory import NotificationStrategyFactory

    mock_notifier = MagicMock()
    mock_notifier.send_notification = AsyncMock(return_value=(True, "Dispatched test email"))
    monkeypatch.setattr(NotificationStrategyFactory, "create_strategy", lambda notif_type, config: mock_notifier)

    # Email (free ₹0)
    res = await async_client.post("/api/test-notification", json={
        "medium": "email",
        "target": "user@example.com"
    })
    assert res.status_code == 200
    assert res.json()["success"] is True

    # Discord (free ₹0)
    res = await async_client.post("/api/test-notification", json={
        "medium": "discord",
        "target": "https://discord.com/api/webhooks/123/xyz"
    })
    assert res.status_code == 200
    assert res.json()["success"] is True


@pytest.mark.asyncio
async def test_test_notification_dynamic_admin_pricing_changes(async_client, monkeypatch):
    from unittest.mock import AsyncMock, MagicMock
    from lib.services.pricing import PricingService
    from lib.services.notification.factory import NotificationStrategyFactory

    mock_notifier = MagicMock()
    mock_notifier.send_notification = AsyncMock(return_value=(True, "Dispatched test alert"))
    monkeypatch.setattr(NotificationStrategyFactory, "create_strategy", lambda notif_type, config: mock_notifier)

    # Admin makes SMS free (0 paise) and Email paid (50 paise)
    PricingService.update_prices(
        admin_uid="test-admin-uid-999",
        admin_email="admin@example.com",
        sms_paise=0,
        whatsapp_paise=100,
        phone_call_paise=150,
        email_paise=50,
        discord_paise=0,
        note="Admin testing free SMS and paid Email policy"
    )

    # SMS is now free: should succeed
    res = await async_client.post("/api/test-notification", json={
        "medium": "sms",
        "target": "9876543210"
    })
    assert res.status_code == 200
    assert res.json()["success"] is True

    # Email is now paid: must be rejected
    res = await async_client.post("/api/test-notification", json={
        "medium": "email",
        "target": "user@example.com"
    })
    assert res.status_code == 400
    assert "only allowed for free mediums" in res.json()["detail"]


@pytest.mark.asyncio
async def test_test_notification_validation_errors(async_client):
    # Empty target
    res = await async_client.post("/api/test-notification", json={
        "medium": "email",
        "target": "   "
    })
    assert res.status_code == 400
    assert "Target recipient/URL/phone is required" in res.json()["detail"]

    # Unsupported medium
    res = await async_client.post("/api/test-notification", json={
        "medium": "telepathy",
        "target": "user@example.com"
    })
    assert res.status_code == 400
    assert "Unsupported notification medium" in res.json()["detail"]



