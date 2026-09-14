# src/Backend/tests/test_profile.py

import pytest

@pytest.mark.asyncio
async def test_get_profile(async_client):
    res = await async_client.get("/api/profile")
    assert res.status_code == 200
    data = res.json()
    assert "preferences" in data
    assert "consents" in data
    assert "wallet_balance_paise" in data

@pytest.mark.asyncio
async def test_update_preferences(async_client):
    payload = {
        "email_enabled": True,
        "whatsapp_enabled": True,
        "whatsapp_phone": "+919876543210",
        "preferred_medium": "whatsapp"
    }
    res = await async_client.put("/api/profile/preferences", json=payload)
    assert res.status_code == 200
    assert res.json()["success"] is True

@pytest.mark.asyncio
async def test_opt_in_and_opt_out(async_client):
    # Opt in to WhatsApp
    res_in = await async_client.post("/api/consent/whatsapp/opt-in", json={"phone_number": "+919876543210"})
    assert res_in.status_code == 200
    assert res_in.json()["success"] is True

    # Opt out of WhatsApp
    res_out = await async_client.post("/api/consent/whatsapp/opt-out")
    assert res_out.status_code == 200
    assert res_out.json()["success"] is True

@pytest.mark.asyncio
async def test_terms_status_and_accept(async_client):
    res_status = await async_client.get("/api/terms/status")
    assert res_status.status_code == 200
    assert res_status.json()["current_version"] == "2.0"

    res_accept = await async_client.post("/api/terms/accept", json={"version": "2.0"})
    assert res_accept.status_code == 200
    assert res_accept.json()["success"] is True
