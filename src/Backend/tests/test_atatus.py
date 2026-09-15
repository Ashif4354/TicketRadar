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


def test_atatus_disabled_with_whitespace_or_empty_key(monkeypatch):
    """When ATATUS_LICENSE_KEY is whitespace or empty, no Atatus feature is activated."""
    monkeypatch.setenv("ATATUS_LICENSE_KEY", "   ")
    from lib.utils import config
    if config.settings:
        monkeypatch.setattr(config.settings, "atatus_license_key", "   ")

    if "main" in sys.modules:
        del sys.modules["main"]
    import main

    assert main.atatus_client is None
    middleware_types = [m.cls.__name__ for m in main.app.user_middleware]
    assert "Atatus" not in middleware_types
    client = TestClient(main.app)
    assert client.get("/health").status_code == 200


def test_atatus_initialization_failure_does_not_break_app(monkeypatch):
    """If Atatus raises an exception during initialization, the app starts cleanly without breaking."""
    monkeypatch.setenv("ATATUS_LICENSE_KEY", "dummy_key")
    from lib.utils import config
    if config.settings:
        monkeypatch.setattr(config.settings, "atatus_license_key", "dummy_key")

    import sys
    monkeypatch.setitem(sys.modules, "atatus", None)

    if "main" in sys.modules:
        del sys.modules["main"]
    import main

    assert main.atatus_client is None
    middleware_types = [m.cls.__name__ for m in main.app.user_middleware]
    assert "Atatus" not in middleware_types
    client = TestClient(main.app)
def test_atatus_user_middleware_sets_user_on_request(monkeypatch):
    """Verify atatus_user_middleware extracts user from JWT Bearer token and sets request.state.user."""
    import jwt
    import main
    from unittest.mock import patch, MagicMock
    from lib.utils import config

    if config.settings:
        monkeypatch.setattr(config.settings, "atatus_license_key", "lic_test_123")
    monkeypatch.setenv("ATATUS_LICENSE_KEY", "lic_test_123")

    token_payload = {
        "uid": "usr_test_abc123",
        "email": "sarah.connor@example.com",
        "name": "Sarah Connor",
    }
    test_token = jwt.encode(token_payload, "test_secret", algorithm="HS256")

    client = TestClient(main.app)
    with patch("atatus.get_client", return_value=MagicMock()), \
         patch("atatus.set_user") as mock_set_user:
        resp = client.get("/health", headers={"Authorization": f"Bearer {test_token}"})
        assert resp.status_code == 200
        mock_set_user.assert_called_with(
            user_id="usr_test_abc123",
            username="Sarah Connor",
            email="sarah.connor@example.com"
        )


def test_atatus_user_middleware_unauthenticated_request_is_permissive():
    """Verify that public endpoints without Authorization header succeed and do not break."""
    import main

    client = TestClient(main.app)
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


def test_atatus_user_middleware_malformed_token_is_permissive():
    """Verify that malformed Authorization tokens are handled gracefully without raising 500."""
    import main

    client = TestClient(main.app)
    resp = client.get("/health", headers={"Authorization": "Bearer not-a-valid-jwt-token"})
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_job_manager_loop_instruments_atatus_transaction(monkeypatch):
    """Verify that _run_job_loop starts a background transaction, sets user, sets outcome, and ends transaction."""
    import asyncio
    from unittest.mock import MagicMock, AsyncMock, patch
    from lib.core.monitor import JobManager
    from lib.core.job import MonitorJob
    from lib.utils import config

    if config.settings:
        monkeypatch.setattr(config.settings, "atatus_license_key", "lic_test_123")
    monkeypatch.setenv("ATATUS_LICENSE_KEY", "lic_test_123")

    job = MonitorJob(
        job_id="test_job_atatus_001",
        params={
            "url": "https://in.bookmyshow.com/buytickets/test-movie-city/movie-city-ET001-MT/20260920",
            "movie_name": "Inception Re-release",
            "date_str": "20260920",
            "theatres": ["PVR: Inorbit Mall"],
        },
        notification_medium="email",
        notification_config={"email": "creator@example.com"},
        check_interval=1,
        created_by="user_job_creator_789",
    )
    job.movie_name = "Inception Re-release"
    job.creator_email = "creator@example.com"

    stop_event = asyncio.Event()

    mock_scraper = AsyncMock()
    # Scraper returns no booking on first check, then we stop
    mock_scraper.check_booking.return_value = (
        False, "Booking not opened", "Inception Re-release", [], ["PVR: Inorbit Mall"]
    )
    mock_scraper.close = AsyncMock()

    mock_atatus_client = MagicMock()
    mock_tx = MagicMock()
    mock_atatus_client.begin_transaction.return_value = mock_tx

    with patch("lib.core.monitor.ScraperFactory.create_scraper", return_value=mock_scraper), \
         patch("atatus.get_client", return_value=mock_atatus_client), \
         patch("atatus.set_transaction_name") as mock_set_name, \
         patch("atatus.set_user") as mock_set_user, \
         patch("atatus.set_transaction_outcome") as mock_set_outcome:

        # Set stop event after a brief delay
        async def stop_soon():
            await asyncio.sleep(0.05)
            stop_event.set()

        asyncio.create_task(stop_soon())

        jm = JobManager()
        await jm._run_job_loop(job, stop_event)

        # Verify Atatus APM background transaction calls
        mock_atatus_client.begin_transaction.assert_called_with("job")
        mock_set_name.assert_called_with("MonitorJob: Inception Re-release")
        mock_set_user.assert_called_with(user_id="user_job_creator_789", email="creator@example.com")
        mock_set_outcome.assert_called_with("success")
        mock_atatus_client.end_transaction.assert_called_with("MonitorJob: Inception Re-release", "success")


@pytest.mark.asyncio
async def test_auth_claims_enrichment_and_atatus_set_user(monkeypatch):
    """Verify that get_current_user_claims enriches claims with name and email, and calls atatus.set_user."""
    from unittest.mock import patch, AsyncMock
    from lib.core.auth import get_current_user_claims

    raw_token_claims = {
        "uid": "usr_auth_999",
        "email": "batman@waynecorp.com",
        "name": "Bruce Wayne",
    }

    monkeypatch.delenv("DISABLE_SECURITY", raising=False)
    from lib.utils import config
    from unittest.mock import MagicMock
    if config.settings:
        monkeypatch.setattr(config.settings, "disable_security", False)
        monkeypatch.setattr(config.settings, "atatus_license_key", "lic_test_123")
    monkeypatch.setenv("ATATUS_LICENSE_KEY", "lic_test_123")

    with patch("lib.core.auth.verify_app_check", new_callable=AsyncMock), \
         patch("lib.core.auth.auth.verify_id_token", return_value=raw_token_claims), \
         patch("atatus.get_client", return_value=MagicMock()), \
         patch("atatus.set_user") as mock_set_user:

        enriched = await get_current_user_claims(authorization="Bearer valid_token")

        assert enriched["uid"] == "usr_auth_999"
        assert enriched["name"] == "Bruce Wayne"
        assert enriched["email"] == "batman@waynecorp.com"
        assert enriched["user_name"] == "Bruce Wayne"

        mock_set_user.assert_called_with(
            user_id="usr_auth_999",
            username="Bruce Wayne",
            email="batman@waynecorp.com"
        )


@pytest.mark.asyncio
async def test_alert_send_instruments_atatus_span_in_job_loop(monkeypatch):
    """Verify that when tickets are found, notifier.send_notification is wrapped with atatus.async_capture_span."""
    import asyncio
    from unittest.mock import MagicMock, AsyncMock, patch
    from lib.core.monitor import JobManager
    from lib.core.job import MonitorJob
    from lib.utils import config

    if config.settings:
        monkeypatch.setattr(config.settings, "atatus_license_key", "lic_test_123")
    monkeypatch.setenv("ATATUS_LICENSE_KEY", "lic_test_123")

    job = MonitorJob(
        job_id="test_job_alert_001",
        params={
            "url": "https://in.bookmyshow.com/buytickets/test-movie-city/movie-city-ET001-MT/20260920",
            "movie_name": "Inception",
            "date_str": "20260920",
            "theatres": ["PVR: Inorbit Mall"],
        },
        notification_medium="email",
        notification_config={"email": "alert_user@example.com"},
        check_interval=1,
        created_by="user_alert_123",
    )
    job.movie_name = "Inception"
    job.creator_email = "alert_user@example.com"

    stop_event = asyncio.Event()

    mock_scraper = AsyncMock()
    # Scraper finds booking!
    mock_scraper.check_booking.return_value = (
        True, "Tickets Available!", "Inception", ["PVR: Inorbit Mall"], []
    )
    mock_scraper.close = AsyncMock()

    mock_notifier = AsyncMock()
    mock_notifier.send_notification.return_value = (True, "Email delivered successfully")

    mock_atatus_client = MagicMock()
    mock_tx = MagicMock()
    mock_atatus_client.begin_transaction.return_value = mock_tx

    span_created = []

    def fake_async_capture_span(name, span_type=None, labels=None, **kwargs):
        span_created.append({"name": name, "span_type": span_type, "labels": labels})
        mock_span = MagicMock()
        from contextlib import asynccontextmanager
        @asynccontextmanager
        async def _ctx():
            yield mock_span
        return _ctx()

    with patch("lib.core.monitor.ScraperFactory.create_scraper", return_value=mock_scraper), \
         patch("lib.core.monitor.NotificationStrategyFactory.create_strategy", return_value=mock_notifier), \
         patch("lib.core.monitor.JobManager.claim_notification_slot", return_value=True), \
         patch("lib.core.monitor.JobManager._save_job_to_firestore"), \
         patch("atatus.get_client", return_value=mock_atatus_client), \
         patch("atatus.async_capture_span", side_effect=fake_async_capture_span):

        jm = JobManager()
        await jm._run_job_loop(job, stop_event)

        # Verify that notification.send.email span was created
        matching_spans = [s for s in span_created if s["name"] == "notification.send.email"]
        assert len(matching_spans) >= 1
        assert matching_spans[0]["span_type"] == "notification"
        assert matching_spans[0]["labels"]["medium"] == "email"
        assert matching_spans[0]["labels"]["job_id"] == "test_job_alert_001"


@pytest.mark.asyncio
async def test_email_strategy_instruments_smtp_span(monkeypatch):
    """Verify EmailNotificationStrategy wraps aiosmtplib.send with atatus.async_capture_span."""
    from unittest.mock import AsyncMock, patch, MagicMock
    from lib.services.notification.email_strategy import EmailNotificationStrategy
    from lib.utils import config

    if config.settings:
        monkeypatch.setattr(config.settings, "environment", "production")
        monkeypatch.setattr(config.settings, "smtp_email", "sender@ticketradar.local")
        monkeypatch.setattr(config.settings, "smtp_password", "secret")
        monkeypatch.setattr(config.settings, "smtp_server", "smtp.test.com")
        monkeypatch.setattr(config.settings, "smtp_port", 587)
        monkeypatch.setattr(config.settings, "atatus_license_key", "lic_test_123")
    monkeypatch.setenv("ATATUS_LICENSE_KEY", "lic_test_123")
    monkeypatch.setenv("ENVIRONMENT", "production")

    strategy = EmailNotificationStrategy("user@example.com")
    span_created = []

    def fake_async_capture_span(name, span_type=None, labels=None, **kwargs):
        span_created.append({"name": name, "span_type": span_type, "labels": labels})
        mock_span = MagicMock()
        from contextlib import asynccontextmanager
        @asynccontextmanager
        async def _ctx():
            yield mock_span
        return _ctx()

    with patch("aiosmtplib.send", new_callable=AsyncMock) as mock_smtp, \
         patch("atatus.get_client", return_value=MagicMock()), \
         patch("atatus.async_capture_span", side_effect=fake_async_capture_span):
        mock_smtp.return_value = None

        success, msg = await strategy.send_notification(
            subject="Alert!",
            movie_name="Matrix",
            date_str="20260920",
            available_theatres=["PVR"],
            unavailable_theatres=[],
            url="https://test.com"
        )
        assert success is True
        matching = [s for s in span_created if s["name"] == "email.smtp.send"]
        assert len(matching) == 1
        assert matching[0]["span_type"] == "notification.email"
        assert matching[0]["labels"]["recipient"] == "user@example.com"


@pytest.mark.asyncio
async def test_twilio_adapter_instruments_sms_span(monkeypatch):
    """Verify TwilioProviderAdapter wraps send_sms with atatus.async_capture_span."""
    from unittest.mock import patch, MagicMock
    from lib.providers.notification.twilio_adapter import TwilioProviderAdapter
    from lib.utils import config

    if config.settings:
        monkeypatch.setattr(config.settings, "atatus_license_key", "lic_test_123")
    monkeypatch.setenv("ATATUS_LICENSE_KEY", "lic_test_123")

    adapter = TwilioProviderAdapter(
        account_sid="AC12345",
        auth_token="token123",
        from_number="+1234567890"
    )

    span_created = []

    def fake_async_capture_span(name, span_type=None, **kwargs):
        span_created.append({"name": name, "span_type": span_type})
        mock_span = MagicMock()
        from contextlib import asynccontextmanager
        @asynccontextmanager
        async def _ctx():
            yield mock_span
        return _ctx()

    mock_msg = MagicMock()
    mock_msg.sid = "SM_test_12345"

    with patch.object(adapter, "_get_client") as mock_client_factory, \
         patch("atatus.get_client", return_value=MagicMock()), \
         patch("atatus.async_capture_span", side_effect=fake_async_capture_span):
        mock_client = MagicMock()
        mock_client.messages.create.return_value = mock_msg
        mock_client_factory.return_value = mock_client

        res = await adapter.send_sms(to="+919876543210", body="Test SMS", idempotency_key="sms_key_1")
        assert res.success is True
        assert res.provider_id == "SM_test_12345"
        assert any(s["name"] == "twilio.send_sms" and s["span_type"] == "notification.sms" for s in span_created)


def test_apm_wrapper_strictly_noop_when_no_license_key(monkeypatch):
    """Verify that all apm module functions act as strict no-ops when license key is empty or not set."""
    from lib.utils import config
    from lib.utils import apm
    from unittest.mock import patch

    monkeypatch.delenv("ATATUS_LICENSE_KEY", raising=False)
    if config.settings:
        monkeypatch.setattr(config.settings, "atatus_license_key", "")

    assert apm.is_atatus_enabled() is False
    assert apm.get_client() is None

    with patch("atatus.set_user") as mock_set_user, \
         patch("atatus.set_transaction_name") as mock_set_tx_name, \
         patch("atatus.set_transaction_outcome") as mock_set_outcome, \
         patch("atatus.get_client") as mock_get_client, \
         patch("atatus.async_capture_span") as mock_span:

        apm.set_user("usr_1", "User One", "user1@example.com")
        apm.set_transaction_name("custom_tx")
        apm.set_transaction_outcome("success")
        apm.capture_exception(RuntimeError("test error"))

        mock_set_user.assert_not_called()
        mock_set_tx_name.assert_not_called()
        mock_set_outcome.assert_not_called()
        mock_get_client.assert_not_called()
        mock_span.assert_not_called()


@pytest.mark.asyncio
async def test_async_capture_span_yields_none_when_disabled(monkeypatch):
    """Verify async_capture_span yields None and executes wrapped block when Atatus is disabled."""
    from lib.utils import config, apm
    from unittest.mock import patch

    monkeypatch.delenv("ATATUS_LICENSE_KEY", raising=False)
    if config.settings:
        monkeypatch.setattr(config.settings, "atatus_license_key", "")

    executed = False
    with patch("atatus.async_capture_span") as mock_span:
        async with apm.async_capture_span("test.span") as span:
            assert span is None
            executed = True

    assert executed is True
    mock_span.assert_not_called()


@pytest.mark.asyncio
async def test_job_loop_runs_without_atatus_when_no_license_key(monkeypatch):
    """Verify JobManager._run_job_loop runs scraping and notification completely without Atatus when license key is empty."""
    import asyncio
    from unittest.mock import MagicMock, AsyncMock, patch
    from lib.core.monitor import JobManager
    from lib.core.job import MonitorJob
    from lib.utils import config

    monkeypatch.delenv("ATATUS_LICENSE_KEY", raising=False)
    if config.settings:
        monkeypatch.setattr(config.settings, "atatus_license_key", "")

    job = MonitorJob(
        job_id="job_no_license_001",
        params={
            "url": "https://in.bookmyshow.com/buytickets/test/ET001/20260920",
            "movie_name": "KGF 3",
            "date_str": "20260920",
            "theatres": ["PVR"],
        },
        notification_medium="email",
        notification_config={"email": "nobody@example.com"},
        check_interval=1,
        created_by="user_no_lic_123",
    )
    job.movie_name = "KGF 3"
    job.creator_email = "nobody@example.com"

    stop_event = asyncio.Event()

    mock_scraper = AsyncMock()
    mock_scraper.check_booking.return_value = (True, "Open!", "KGF 3", ["PVR"], [])
    mock_scraper.close = AsyncMock()

    mock_notifier = AsyncMock()
    mock_notifier.send_notification.return_value = (True, "Sent!")

    with patch("lib.core.monitor.ScraperFactory.create_scraper", return_value=mock_scraper), \
         patch("lib.core.monitor.NotificationStrategyFactory.create_strategy", return_value=mock_notifier), \
         patch("lib.core.monitor.JobManager.claim_notification_slot", return_value=True), \
         patch("lib.core.monitor.JobManager._save_job_to_firestore"), \
         patch("atatus.get_client") as mock_get_client, \
         patch("atatus.async_capture_span") as mock_capture_span:

        jm = JobManager()
        await jm._run_job_loop(job, stop_event)

        # Atatus must not have been touched
        mock_get_client.assert_not_called()
        mock_capture_span.assert_not_called()


@pytest.mark.asyncio
async def test_email_strategy_send_notification_without_license_key(monkeypatch):
    """Verify EmailNotificationStrategy sends email without calling Atatus when license key is empty."""
    from unittest.mock import AsyncMock, patch
    from lib.services.notification.email_strategy import EmailNotificationStrategy
    from lib.utils import config

    monkeypatch.delenv("ATATUS_LICENSE_KEY", raising=False)
    if config.settings:
        monkeypatch.setattr(config.settings, "environment", "production")
        monkeypatch.setattr(config.settings, "smtp_email", "sender@ticketradar.local")
        monkeypatch.setattr(config.settings, "smtp_password", "secret")
        monkeypatch.setattr(config.settings, "smtp_server", "smtp.test.com")
        monkeypatch.setattr(config.settings, "smtp_port", 587)
        monkeypatch.setattr(config.settings, "atatus_license_key", "")
    monkeypatch.setenv("ENVIRONMENT", "production")

    strategy = EmailNotificationStrategy("user_no_apm@example.com")

    with patch("aiosmtplib.send", new_callable=AsyncMock) as mock_smtp, \
         patch("atatus.async_capture_span") as mock_span:
        mock_smtp.return_value = None

        success, msg = await strategy.send_notification(
            subject="Alert!",
            movie_name="Matrix",
            date_str="20260920",
            available_theatres=["PVR"],
            unavailable_theatres=[],
            url="https://test.com"
        )
        assert success is True
        mock_smtp.assert_called_once()
        mock_span.assert_not_called()


@pytest.mark.asyncio
async def test_twilio_adapter_send_sms_without_license_key(monkeypatch):
    """Verify TwilioProviderAdapter sends SMS without calling Atatus when license key is empty."""
    from unittest.mock import patch, MagicMock
    from lib.providers.notification.twilio_adapter import TwilioProviderAdapter
    from lib.utils import config

    monkeypatch.delenv("ATATUS_LICENSE_KEY", raising=False)
    if config.settings:
        monkeypatch.setattr(config.settings, "atatus_license_key", "")

    adapter = TwilioProviderAdapter(
        account_sid="AC12345",
        auth_token="token123",
        from_number="+1234567890"
    )

    mock_msg = MagicMock()
    mock_msg.sid = "SM_no_license_123"

    with patch.object(adapter, "_get_client") as mock_client_factory, \
         patch("atatus.async_capture_span") as mock_span:
        mock_client = MagicMock()
        mock_client.messages.create.return_value = mock_msg
        mock_client_factory.return_value = mock_client

        res = await adapter.send_sms(to="+919876543210", body="Hello without APM", idempotency_key="sms_no_apm")
        assert res.success is True
        assert res.provider_id == "SM_no_license_123"
        mock_span.assert_not_called()