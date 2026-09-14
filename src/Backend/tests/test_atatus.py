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


def test_logs_dir_resolution(monkeypatch, tmp_path):
    """Verify that get_logs_dir resolves to src/Backend/logs by default and respects LOGS_DIR."""
    from lib.utils.logger import get_logs_dir

    monkeypatch.delenv("LOGS_DIR", raising=False)
    default_dir = get_logs_dir()
    assert default_dir.endswith(os.path.join("src", "Backend", "logs"))
    assert os.path.exists(default_dir)

    custom_dir = str(tmp_path / "custom_logs")
    monkeypatch.setenv("LOGS_DIR", custom_dir)
    resolved = get_logs_dir()
    assert resolved == os.path.abspath(custom_dir)
    assert os.path.exists(resolved)


def test_file_log_correlation_and_clean_console(monkeypatch, tmp_path):
    """
    Verify that:
    1. Endpoint requests are captured in logs.
    2. Atatus trace correlation is written to the file handler in src/Backend/logs/ (or LOGS_DIR).
    3. Console output remains clean and does NOT contain Atatus correlation tags.
    """
    import io
    import logging
    from lib.utils.logger import reset_file_handler, configure_logging, is_console_handler

    custom_logs_dir = str(tmp_path / "test_logs")
    monkeypatch.setenv("LOGS_DIR", custom_logs_dir)
    reset_file_handler()

    test_key = "lic_apm_test_log_correlation_key"
    monkeypatch.setenv("ATATUS_LICENSE_KEY", test_key)
    monkeypatch.setenv("ATATUS_DISABLE_SEND", "true")

    from lib.utils import config
    if config.settings:
        monkeypatch.setattr(config.settings, "atatus_license_key", test_key)

    # Re-import main to re-run initialization with Atatus
    if "main" in sys.modules:
        del sys.modules["main"]
    import main

    # Intercept console output on root logger
    root_logger = logging.getLogger()
    console_capture = io.StringIO()
    console_handler = [h for h in root_logger.handlers if is_console_handler(h)][0]
    original_stream = console_handler.stream
    console_handler.stream = console_capture

    try:
        client = TestClient(main.app)
        resp = client.get("/health")
        assert resp.status_code == 200

        resp_root = client.get("/")
        assert resp_root.status_code == 200

        # Flush all handlers
        for h in root_logger.handlers:
            h.flush()

        # 1. Verify file logs contain endpoint calls AND Atatus trace correlation
        log_file = os.path.join(custom_logs_dir, "app.log")
        assert os.path.exists(log_file)
        with open(log_file, "r", encoding="utf-8") as f:
            file_logs = f.read()

        assert "GET /health" in file_logs
        assert "GET /" in file_logs
        assert "atatus trace.id=" in file_logs

        # 2. Verify console logs contain endpoint calls but NO Atatus trace correlation
        console_logs = console_capture.getvalue()
        assert "GET /health" in console_logs
        assert "GET /" in console_logs
        assert "atatus trace.id=" not in console_logs

    finally:
        console_handler.stream = original_stream
        reset_file_handler()
        if main.atatus_client is not None:
            try:
                main.atatus_client.close()
            except Exception:
                pass


def test_redundant_logs_suppression():
    """Verify that child loggers propagate cleanly without duplicate handlers and uvicorn.access is silenced."""
    import logging
    from lib.utils.logger import configure_logging, setup_logger

    configure_logging(enable_atatus_file_correlation=False)

    tr_logger = setup_logger("ticketradar")
    assert tr_logger.propagate is True
    assert len(tr_logger.handlers) == 0

    api_logger = logging.getLogger("ticketradar.api")
    assert api_logger.propagate is True
    assert len(api_logger.handlers) == 0

    uvicorn_access = logging.getLogger("uvicorn.access")
    assert uvicorn_access.propagate is False
    assert len(uvicorn_access.handlers) == 0


def test_gcp_filter_captures_atatus_trace_context():
    """Verify FrameworkLogFilter in GCPLoggingService enriches log records with Atatus trace context."""
    import logging
    from lib.services.gcp_logger import FrameworkLogFilter

    filt = FrameworkLogFilter()
    record = logging.LogRecord(
        name="ticketradar.api",
        level=logging.INFO,
        pathname=__file__,
        lineno=10,
        msg="Test message",
        args=(),
        exc_info=None,
    )
    record.atatus_trace_id = "test-atatus-trace-123"
    record.atatus_span_id = "test-atatus-span-456"
    record.atatus_transaction_id = "test-atatus-tx-789"

    assert filt.filter(record) is True
    assert record._labels["trace_id"] == "test-atatus-trace-123"
    assert record.json_fields["trace_id"] == "test-atatus-trace-123"
    assert record._labels["span_id"] == "test-atatus-span-456"
    assert record.json_fields["transaction_id"] == "test-atatus-tx-789"


    