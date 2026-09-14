import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from lib.services.notification.templates import EmailTemplates, MessageTemplates, DiscordTemplates
from lib.services.notification.email_strategy import EmailNotificationStrategy
from lib.services.notification.sms_strategy import SMSNotificationStrategy
from lib.services.notification.whatsapp_strategy import WhatsAppNotificationStrategy
from lib.services.notification.discord_strategy import DiscordWebhookNotificationStrategy
from lib.services.notification import user_mailer

def test_email_templates_catalog():
    # 1. Signup
    tmpl = EmailTemplates.get_template("signup", name="John Doe")
    assert "John Doe" in tmpl["html"]
    assert "Welcome" in tmpl["subject"]

    # 2. Payment success & failed
    ps = EmailTemplates.get_template("payment_success", amount_inr="10.00", order_id="cf_123")
    assert "₹10.00" in ps["html"]
    assert "cf_123" in ps["html"]

    pf = EmailTemplates.get_template("payment_failed", order_id="cf_fail", error_reason="Declined by bank")
    assert "cf_fail" in pf["html"]
    assert "Declined by bank" in pf["html"]

    # 3. Call 3x unanswered with number called and metadata
    c3x = EmailTemplates.get_template(
        "call_3x_unanswered",
        movie_name="Deadpool & Wolverine",
        phone_number="+919876543210",
        attempts=3,
        cinema_name="PVR Cinemas",
        booking_url="https://in.bookmyshow.com/test",
    )
    assert "+919876543210" in c3x["html"]
    assert "Deadpool" in c3x["html"]
    assert "Deadpool & Wolverine" in c3x["text"]
    assert "PVR Cinemas" in c3x["html"]
    assert "3" in c3x["html"]

    # 4. Call success with number called and metadata
    cs = EmailTemplates.get_template(
        "call_success",
        movie_name="Gladiator II",
        phone_number="+919876543210",
        duration="35s",
        cinema_name="INOX Megaplex",
    )
    assert "+919876543210" in cs["html"]
    assert "Gladiator II" in cs["html"]
    assert "35s" in cs["html"]

    # 5. Wallet transactions
    wt = EmailTemplates.get_template("wallet_topup_success", amount_inr="50.00", balance_inr="75.00")
    assert "₹50.00" in wt["html"]
    assert "₹75.00" in wt["html"]

    wd = EmailTemplates.get_template("wallet_debit", amount_inr="1.50", balance_inr="73.50", reason="Voice Call Alert")
    assert "₹1.50" in wd["html"]
    assert "Voice Call Alert" in wd["html"]

    wc = EmailTemplates.get_template("wallet_credit", amount_inr="5.00", balance_inr="78.50", reason="Promotional Bonus")
    assert "₹5.00" in wc["html"]

    # 6. Refund with reason
    rf = EmailTemplates.get_template("refund", amount_inr="1.50", reason="Delivery failure", refund_id="rf_001")
    assert "₹1.50" in rf["html"]
    assert "Delivery failure" in rf["html"]
    assert "rf_001" in rf["html"]

    # 7. Admin pricing changed
    ap = EmailTemplates.get_template(
        "admin_pricing_changed",
        admin_email="admin@example.com",
        sms_inr="0.65",
        whatsapp_inr="1.15",
        call_inr="1.80",
        email_inr="0.00",
        discord_inr="0.00",
        note="Vendor tariff revision",
    )
    assert "admin@example.com" in ap["html"]
    assert "₹0.65" in ap["html"]
    assert "Vendor tariff revision" in ap["html"]

    # 8. Job created & cancelled
    jc = EmailTemplates.get_template("job_created", movie_name="Interstellar", cinema_name="IMAX", job_id="job_789")
    assert "Interstellar" in jc["html"]
    assert "job_789" in jc["html"]

    jcan = EmailTemplates.get_template("job_cancelled", movie_name="Interstellar", reason="User requested")
    assert "User requested" in jcan["html"]

    # 9. Notification sent & failed
    ns = EmailTemplates.get_template("notification_sent", movie_name="Avatar 3", medium="SMS")
    assert "SMS" in ns["html"]

    nf = EmailTemplates.get_template("notification_failed", movie_name="Avatar 3", medium="WhatsApp", error_details="Unreachable")
    assert "Unreachable" in nf["html"]

    # 10. Access granted
    ag = EmailTemplates.get_template("access_granted", name="Alice")
    assert "Alice" in ag["html"]

    # 11. Unknown template KeyError
    with pytest.raises(KeyError):
        EmailTemplates.get_template("nonexistent_template")


def test_message_templates_catalog():
    alert_sms = MessageTemplates.get_template(
        "alert",
        movie_name="Dune 2",
        cinema_name="PVR",
        booking_url="https://in.bookmyshow.com/dune",
    )
    assert "Dune 2" in alert_sms["body"]
    assert "https://in.bookmyshow.com/dune" in alert_sms["body"]

    call_retry = MessageTemplates.get_template(
        "call_retry",
        movie_name="Dune 2",
        attempts=3,
        phone_number="+919876543210",
    )
    assert "+919876543210" in call_retry["body"]
    assert "3" in call_retry["body"]


def test_discord_templates_catalog():
    payload = DiscordTemplates.get_template(
        "alert",
        movie_name="Oppenheimer",
        cinema_name="IMAX Laser",
        date_str="2026-09-20",
        available_theatres=["IMAX Laser"],
        unavailable_theatres=[],
        url="https://in.bookmyshow.com/oppenheimer",
        details="English | IMAX 2D",
    )
    assert "embeds" in payload
    assert "Oppenheimer" in payload["embeds"][0]["title"]
    assert "IMAX Laser" in payload["embeds"][0]["description"]


def test_strategy_template_inheritance():
    from lib.services.notification.phone_call_strategy import PhoneCallNotificationStrategy

    email_strat = EmailNotificationStrategy("test@example.com")
    assert hasattr(email_strat, "get_template")
    assert issubclass(EmailNotificationStrategy, EmailTemplates)
    t = email_strat.get_template("signup", name="Bob")
    assert "Bob" in t["html"]

    sms_strat = SMSNotificationStrategy("+919876543210", MagicMock())
    assert hasattr(sms_strat, "get_template")
    assert issubclass(SMSNotificationStrategy, MessageTemplates)

    wa_strat = WhatsAppNotificationStrategy("+919876543210", MagicMock())
    assert hasattr(wa_strat, "get_template")
    assert issubclass(WhatsAppNotificationStrategy, MessageTemplates)

    discord_strat = DiscordWebhookNotificationStrategy("https://discord.com/api/webhooks/test")
    assert hasattr(discord_strat, "get_template")
    assert issubclass(DiscordWebhookNotificationStrategy, DiscordTemplates)

    call_strat = PhoneCallNotificationStrategy("+919876543210", MagicMock())
    assert hasattr(call_strat, "get_template")
    assert issubclass(PhoneCallNotificationStrategy, MessageTemplates)


@pytest.mark.asyncio
async def test_user_mailer_dispatch_helpers():
    with patch("lib.services.notification.user_mailer._send_rendered_email", new_callable=AsyncMock) as mock_send:
        mock_send.return_value = (True, "Sent")
        await user_mailer.send_signup_email("test@example.com", user_name="Charlie")
        assert mock_send.called
        args, kwargs = mock_send.call_args
        assert kwargs["to_email"] == "test@example.com"
        assert kwargs["template_name"] == "signup"

    with patch("lib.services.notification.user_mailer._send_rendered_email", new_callable=AsyncMock) as mock_send:
        mock_send.return_value = (True, "Sent")
        await user_mailer.send_wallet_topup_success_email("test@example.com", user_name="Charlie", amount_inr=50.00, new_balance_inr=75.00)
        assert mock_send.called
        args, kwargs = mock_send.call_args
        assert kwargs["template_name"] == "wallet_topup_success"
        assert kwargs["amount_inr"] == 50.00

    with patch("lib.services.notification.user_mailer._send_rendered_email", new_callable=AsyncMock) as mock_send:
        mock_send.return_value = (True, "Sent")
        await user_mailer.send_admin_pricing_changed_email(
            admin_email="admin@example.com",
            admin_name="Admin User",
            old_prices={"sms_paise": 50},
            new_prices={"sms_paise": 60, "whatsapp_paise": 110, "phone_call_paise": 160, "email_paise": 0, "discord_paise": 0},
            note="Tariff update",
        )
        assert mock_send.called
        args, kwargs = mock_send.call_args
        assert kwargs["template_name"] == "admin_pricing_changed"

    with patch("lib.services.notification.user_mailer._send_rendered_email", new_callable=AsyncMock) as mock_send:
        mock_send.return_value = (True, "Sent")
        await user_mailer.send_call_unanswered_email("test@example.com", "Bob", "+919876543210", "Dune 2", "2026-09-20")
        assert mock_send.called
        assert mock_send.call_args[1]["template_name"] == "call_unanswered"

    with patch("lib.services.notification.user_mailer._send_rendered_email", new_callable=AsyncMock) as mock_send:
        mock_send.return_value = (True, "Sent")
        await user_mailer.send_call_success_email("test@example.com", "Bob", "+919876543210", "Dune 2", "2026-09-20", call_duration_seconds=25)
        assert mock_send.called
        assert mock_send.call_args[1]["template_name"] == "call_success"

    with patch("lib.services.notification.user_mailer._send_rendered_email", new_callable=AsyncMock) as mock_send:
        mock_send.return_value = (True, "Sent")
        await user_mailer.send_payment_failed_email("test@example.com", "Bob", "order_123", 10.0)
        assert mock_send.called
        assert mock_send.call_args[1]["template_name"] == "payment_failed"

    with patch("lib.services.notification.user_mailer._send_rendered_email", new_callable=AsyncMock) as mock_send:
        mock_send.return_value = (True, "Sent")
        await user_mailer.send_wallet_topup_failed_email("test@example.com", "Bob", 10.0, "order_123")
        assert mock_send.called
        assert mock_send.call_args[1]["template_name"] == "wallet_topup_failed"

    with patch("lib.services.notification.user_mailer._send_rendered_email", new_callable=AsyncMock) as mock_send:
        mock_send.return_value = (True, "Sent")
        await user_mailer.send_refund_email("test@example.com", "Bob", 5.0, "Job cancelled")
        assert mock_send.called
        assert mock_send.call_args[1]["template_name"] == "refund"

    with patch("lib.services.notification.user_mailer._send_rendered_email", new_callable=AsyncMock) as mock_send:
        mock_send.return_value = (True, "Sent")
        await user_mailer.send_job_cancelled_email("test@example.com", "Bob", "job_1", "Dune 2", 5.0)
        assert mock_send.called
        assert mock_send.call_args[1]["template_name"] == "job_cancelled"

    with patch("lib.services.notification.user_mailer._send_rendered_email", new_callable=AsyncMock) as mock_send:
        mock_send.return_value = (True, "Sent")
        await user_mailer.send_notification_sent_email("test@example.com", "Bob", "Dune 2", "SMS")
        assert mock_send.called
        assert mock_send.call_args[1]["template_name"] == "notification_sent"

    with patch("lib.services.notification.user_mailer._send_rendered_email", new_callable=AsyncMock) as mock_send:
        mock_send.return_value = (True, "Sent")
        await user_mailer.send_notification_failed_email("test@example.com", "Bob", "job_1", "Dune 2", "SMS", "Network err")
        assert mock_send.called
        assert mock_send.call_args[1]["template_name"] == "notification_failed"

