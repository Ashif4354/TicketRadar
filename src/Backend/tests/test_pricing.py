# src/Backend/tests/test_pricing.py

import pytest
from lib.services.pricing import PricingService

def test_pricing_defaults():
    prices = PricingService.get_current_prices()
    assert prices["sms_paise"] == 50
    assert prices["whatsapp_paise"] == 100
    assert prices["phone_call_paise"] == 150
    assert prices["email_paise"] == 0
    assert prices["discord_paise"] == 0

def test_pricing_get_price_for_medium():
    sms_p, _ = PricingService.get_price_for_medium("sms")
    assert sms_p == 50

    wa_p, _ = PricingService.get_price_for_medium("whatsapp")
    assert wa_p == 100

    call_p, _ = PricingService.get_price_for_medium("phone_call")
    assert call_p == 150

    em_p, _ = PricingService.get_price_for_medium("email")
    assert em_p == 0

def test_pricing_update_requires_note():
    with pytest.raises(ValueError, match="explanation note is required"):
        PricingService.update_prices(
            admin_uid="admin1",
            admin_email="admin@example.com",
            sms_paise=75,
            whatsapp_paise=120,
            phone_call_paise=200,
            note=""  # Empty note must be rejected!
        )

def test_pricing_update_success():
    new_cfg = PricingService.update_prices(
        admin_uid="admin1",
        admin_email="admin@example.com",
        sms_paise=60,
        whatsapp_paise=110,
        phone_call_paise=175,
        note="Telecom provider price increase"
    )
    assert new_cfg["sms_paise"] == 60
    assert new_cfg["whatsapp_paise"] == 110
    assert new_cfg["phone_call_paise"] == 175
    assert new_cfg["is_current"] is True

    # Verify current prices reflect update
    curr = PricingService.get_current_prices()
    assert curr["sms_paise"] == 60
