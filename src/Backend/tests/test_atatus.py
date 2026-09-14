import os
import sys
import importlib
import pytest
from fastapi.testclient import TestClient

backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)


def test_get_app_version():
    """Verify that APP_VERSION is correctly read from pyproject.toml."""
    import main
    import tomllib
    pyproject_path = os.path.join(backend_dir, "pyproject.toml")
    with open(pyproject_path, "rb") as f:
        expected = tomllib.load(f)["project"]["version"]
    version = main.get_app_version()
    assert version == expected
    assert main.APP_VERSION == expected


def test_settings_reads_atatus_license_key_from_env(monkeypatch):
    """Verify that Settings reads ATATUS_LICENSE_KEY from the environment."""
    test_key = "lic_apm_from_env_999"
    monkeypatch.setenv("ATATUS_LICENSE_KEY", test_key)
    from lib.utils.config import Settings
    s = Settings()
    assert s.atatus_license_key == test_key


def test_atatus_uninstrumented_when_no_license_key(monkeypatch):
    """When ATATUS_LICENSE_KEY is not set, Atatus client and middleware are not added."""
    monkeypatch.delenv("ATATUS_LICENSE_KEY", raising=False)
    from lib.utils import config
    if config.settings:
        monkeypatch.setattr(config.settings, "atatus_license_key", "")

    # Re-import main to re-run module-level initialization
    if "main" in sys.modules:
        del sys.modules["main"]
    import main

    assert main.atatus_client is None
    middleware_types = [m.cls.__name__ for m in main.app.user_middleware]
    assert "Atatus" not in middleware_types

    # Ensure app endpoints still function normally
    client = TestClient(main.app)
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["version"] == "2.0.0"


def test_atatus_instrumented_when_license_key_provided(monkeypatch):
    """When ATATUS_LICENSE_KEY is set, Atatus client and middleware are initialized with all required configurations."""
    test_key = "lic_apm_mock_test_key_12345"
    monkeypatch.setenv("ATATUS_LICENSE_KEY", test_key)
    monkeypatch.setenv("ATATUS_DISABLE_SEND", "true")
    from lib.utils import config
    if config.settings:
        monkeypatch.setattr(config.settings, "atatus_license_key", test_key)

    # Re-import main to re-run module-level initialization with license key
    if "main" in sys.modules:
        del sys.modules["main"]
    import main

    assert main.atatus_client is not None
    cfg = main.atatus_client.config
    assert cfg.license_key == test_key
    assert cfg.version == "2.0.0"
    assert cfg.environment == main.ENVIRONMENT
    assert cfg.tracing is True
    assert cfg.analytics is True
    assert cfg.analytics_capture_outgoing is True
    assert cfg.capture_body == "all"

    # Middleware should be added
    middleware_types = [m.cls.__name__ for m in main.app.user_middleware]
    assert "Atatus" in middleware_types
    # Atatus should be the outermost middleware (first in user_middleware list)
    assert main.app.user_middleware[0].cls.__name__ == "Atatus"

    # Clean up client background threads
    try:
        main.atatus_client.close()
    except Exception:
        pass


def test_health_endpoint_returns_dynamic_version():
    """Verify that /health reports the version taken from pyproject.toml."""
    import main
    client = TestClient(main.app)
    resp = client.get("/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert data["version"] == "2.0.0"
    