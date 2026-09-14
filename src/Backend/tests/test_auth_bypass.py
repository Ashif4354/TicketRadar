# src/Backend/tests/test_auth_bypass.py

import os
import pytest
from unittest.mock import MagicMock
from fastapi import HTTPException
from httpx import AsyncClient, ASGITransport

from main import app
from lib.core import auth
from lib.core.auth import (
    get_current_user_claims,
    get_authorized_user,
    get_admin_user,
    DEV_MOCK_CLAIMS,
    is_security_disabled,
)
from api.dependencies import get_user_details


@pytest.mark.asyncio
async def test_auth_bypass_dependencies_when_security_disabled(monkeypatch):
    monkeypatch.setenv("DISABLE_SECURITY", "true")
    from lib.utils.config import settings
    if settings:
        monkeypatch.setattr(settings, "disable_security", True)

    assert is_security_disabled() is True

    # 1. get_current_user_claims without token provides DEV_MOCK_CLAIMS
    claims = await get_current_user_claims(authorization=None)
    assert claims["uid"] == DEV_MOCK_CLAIMS["uid"]
    assert claims["email"] == DEV_MOCK_CLAIMS["email"]
    assert claims["authorized"] is True
    assert claims["role"] == "admin"

    # 2. get_authorized_user allows through
    auth_user = await get_authorized_user(claims)
    assert auth_user["authorized"] is True

    # 3. get_admin_user rejects with 403 when security is disabled
    with pytest.raises(HTTPException) as exc_info_admin:
        await get_admin_user(claims)
    assert exc_info_admin.value.status_code == 403
    assert exc_info_admin.value.detail == "Admin panel is disabled because DISABLE_SECURITY is true"


@pytest.mark.asyncio
async def test_auth_bypass_unauthenticated_requests(monkeypatch):
    """Directly hits endpoints with no Authorization header and no overrides."""
    monkeypatch.setenv("DISABLE_SECURITY", "true")
    from lib.utils.config import settings
    if settings:
        monkeypatch.setattr(settings, "disable_security", True)

    # Ensure no dependency overrides
    app.dependency_overrides.clear()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Admin counts endpoint protected by Depends(get_admin_user) rejects with 403
        res_admin = await client.get("/admin/counts")
        assert res_admin.status_code == 403
        assert res_admin.json()["detail"] == "Admin panel is disabled because DISABLE_SECURITY is true"

        # Profile endpoint protected by Depends(get_authorized_user)
        res_profile = await client.get("/api/profile")
        assert res_profile.status_code == 200


@pytest.mark.asyncio
async def test_auth_enforced_when_security_enabled(monkeypatch):
    monkeypatch.setenv("DISABLE_SECURITY", "false")
    from lib.utils.config import settings
    if settings:
        monkeypatch.setattr(settings, "disable_security", False)

    assert is_security_disabled() is False

    # Missing authorization header raises 401
    with pytest.raises(HTTPException) as exc_info:
        await get_current_user_claims(authorization=None)
    assert exc_info.value.status_code == 401

    # Unauthorized claim raises 403 in get_authorized_user
    with pytest.raises(HTTPException) as exc_info_auth:
        await get_authorized_user({"uid": "test", "authorized": False})
    assert exc_info_auth.value.status_code == 403

    # Non-admin role raises 403 in get_admin_user
    with pytest.raises(HTTPException) as exc_info_admin:
        await get_admin_user({"uid": "test", "role": "user"})
    assert exc_info_admin.value.status_code == 403


def test_get_user_details_dev_mock():
    name, email, photo = get_user_details("dev-user-001", DEV_MOCK_CLAIMS)
    assert name == "Dev Admin"
    assert email == "dev@ticketradar.local"


@pytest.mark.asyncio
async def test_auth_bypass_overrides_non_admin_and_blocked_claims(monkeypatch):
    """Even if a token originally has role='user' or blocked=True, security disabled forces admin & authorized."""
    monkeypatch.setenv("DISABLE_SECURITY", "true")
    from lib.utils.config import settings
    if settings:
        monkeypatch.setattr(settings, "disable_security", True)

    import jwt
    dummy_payload = {
        "uid": "custom-user-999",
        "email": "user@example.com",
        "role": "user",
        "authorized": False,
        "blocked": True,
    }
    raw_jwt = jwt.encode(dummy_payload, "a_very_secret_key_that_is_at_least_32_bytes_long", algorithm="HS256")

    claims = await get_current_user_claims(authorization=f"Bearer {raw_jwt}")
    assert claims["uid"] == "custom-user-999"
    assert claims["role"] == "admin"
    assert claims["authorized"] is True
    assert claims["blocked"] is False

    auth_user = await get_authorized_user(claims)
    assert auth_user["authorized"] is True
    assert auth_user["role"] == "admin"

    with pytest.raises(HTTPException) as exc_info_admin:
        await get_admin_user(claims)
    assert exc_info_admin.value.status_code == 403
    assert exc_info_admin.value.detail == "Admin panel is disabled because DISABLE_SECURITY is true"


@pytest.mark.asyncio
async def test_terms_service_and_recaptcha_bypassed_when_security_disabled(monkeypatch):
    monkeypatch.setenv("DISABLE_SECURITY", "true")
    from lib.utils.config import settings
    if settings:
        monkeypatch.setattr(settings, "disable_security", True)

    from lib.services.terms import TermsService
    from api.dependencies import verify_recaptcha, require_terms_accepted

    assert TermsService.check_terms_accepted("any-random-uid") is True
    assert await verify_recaptcha(None) is True
    assert await require_terms_accepted(None) is True


@pytest.mark.asyncio
async def test_api_config_reports_disable_security(monkeypatch):
    monkeypatch.setenv("DISABLE_SECURITY", "true")
    from lib.utils.config import settings
    if settings:
        monkeypatch.setattr(settings, "disable_security", True)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.get("/api/config")
        assert res.status_code == 200
        data = res.json()
        assert data["disable_security"] is True


@pytest.mark.asyncio
async def test_api_config_reports_providers(monkeypatch):
    from lib.utils.config import settings
    if settings:
        monkeypatch.setattr(settings, "payment_gateway", "cashfree")
        monkeypatch.setattr(settings, "notification_provider", "twilio")

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.get("/api/config")
        assert res.status_code == 200
        data = res.json()
        assert data["payment_gateway"] == "cashfree"
        assert data["notification_provider"] == "twilio"


@pytest.mark.asyncio
async def test_disable_approval_bypass(monkeypatch):
    monkeypatch.setenv("DISABLE_SECURITY", "false")
    monkeypatch.setenv("DISABLE_APPROVAL", "true")
    from lib.utils.config import settings
    if settings:
        monkeypatch.setattr(settings, "disable_security", False)
        monkeypatch.setattr(settings, "disable_approval", True)

    from lib.core.auth import is_approval_disabled, get_authorized_user

    assert is_approval_disabled() is True

    # User that is blocked and not authorized
    unauthorized_claims = {
        "uid": "blocked-user-456",
        "email": "blocked@example.com",
        "authorized": False,
        "blocked": True,
        "role": "user"
    }

    # Under DISABLE_APPROVAL=true, should be allowed through freely
    auth_user = await get_authorized_user(unauthorized_claims)
    assert auth_user["authorized"] is True
    assert auth_user["blocked"] is False

    # Also verify /api/config reports disable_approval
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.get("/api/config")
        assert res.status_code == 200
        assert res.json()["disable_approval"] is True


@pytest.mark.asyncio
async def test_disable_security_overrides_environment_to_development(monkeypatch):
    """When DISABLE_SECURITY=true and ENVIRONMENT=production, ENVIRONMENT is forced to development."""
    from lib.utils.config import settings
    from lib.core.auth import get_environment

    monkeypatch.setenv("DISABLE_SECURITY", "true")
    monkeypatch.setenv("ENVIRONMENT", "production")
    if settings:
        monkeypatch.setattr(settings, "disable_security", True)
        monkeypatch.setattr(settings, "environment", "production")

    # get_environment should force 'development'
    assert get_environment() == "development"


@pytest.mark.asyncio
async def test_production_enforces_app_check(monkeypatch):
    """When ENVIRONMENT=production and DISABLE_SECURITY=false, verify_app_check raises 401 on missing header."""
    from lib.utils.config import settings
    from lib.core.auth import verify_app_check

    monkeypatch.setenv("DISABLE_SECURITY", "false")
    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.setenv("DISABLE_APP_CHECK", "false")
    if settings:
        monkeypatch.setattr(settings, "disable_security", False)
        monkeypatch.setattr(settings, "environment", "production")

    with pytest.raises(HTTPException) as exc_info:
        await verify_app_check(x_firebase_appcheck=None)
    assert exc_info.value.status_code == 401
    assert exc_info.value.detail == "App Check token is required."


@pytest.mark.asyncio
async def test_test_environment_skips_admin_notifications(monkeypatch):
    """When ENVIRONMENT=test, admin Discord notifications are suppressed."""
    from lib.services.notification.admin_notifier import send_admin_discord_embed

    monkeypatch.setenv("ENVIRONMENT", "test")
    success, msg = await send_admin_discord_embed("Test Title", "Test Desc", 0x00FF00)
    assert success is True
    assert "Skipped in test environment" in msg


@pytest.mark.asyncio
async def test_api_config_reports_environment(monkeypatch):
    """Verify /api/config returns active environment."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.get("/api/config")
        assert res.status_code == 200
        data = res.json()
        assert "environment" in data
        assert data["environment"] == "test"


@pytest.mark.asyncio
async def test_test_environment_skips_admin_emails(monkeypatch):
    """When ENVIRONMENT=test, admin and system email dispatch is suppressed."""
    from lib.services.notification.user_mailer import send_admin_pricing_changed_email

    monkeypatch.setenv("ENVIRONMENT", "test")
    success, msg = await send_admin_pricing_changed_email(
        admin_email="admin@example.com",
        admin_name="Admin",
        old_prices=None,
        new_prices=None,
        note="Test pricing note"
    )
    assert success is True
    assert "Skipped in test environment" in msg



