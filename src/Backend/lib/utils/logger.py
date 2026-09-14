# src/Backend/lib/utils/logger.py

import os
import sys
import logging
from logging.handlers import RotatingFileHandler
from typing import Optional

from .config import LOG_FORMAT

_file_handler: Optional[RotatingFileHandler] = None


def get_logs_dir() -> str:
    """
    Resolves the directory where log files are stored.
    Always targets the logs/ directory in src/Backend (or LOGS_DIR env var if set).
    Works seamlessly when run locally (e.g. 'make run') or with docker compose.
    """
    env_logs_dir = os.getenv("LOGS_DIR")
    if env_logs_dir:
        logs_path = os.path.abspath(env_logs_dir)
        os.makedirs(logs_path, exist_ok=True)
        return logs_path

    current_dir = os.path.dirname(os.path.abspath(__file__))  # src/Backend/lib/utils
    backend_dir = os.path.abspath(os.path.join(current_dir, "..", ".."))  # src/Backend
    logs_path = os.path.join(backend_dir, "logs")
    os.makedirs(logs_path, exist_ok=True)
    return logs_path


def reset_file_handler() -> None:
    """Closes and resets the singleton file handler (useful for testing or reconfiguration)."""
    global _file_handler
    if _file_handler is not None:
        try:
            root_logger = logging.getLogger()
            if _file_handler in root_logger.handlers:
                root_logger.removeHandler(_file_handler)
            _file_handler.close()
        except Exception:
            pass
        _file_handler = None


def get_file_handler(formatter: Optional[logging.Formatter] = None) -> RotatingFileHandler:
    """
    Returns a singleton RotatingFileHandler writing to logs/app.log in src/Backend.
    """
    global _file_handler
    if _file_handler is not None:
        if formatter is not None:
            _file_handler.setFormatter(formatter)
        return _file_handler

    logs_dir = get_logs_dir()
    log_file = os.path.join(logs_dir, "app.log")
    _file_handler = RotatingFileHandler(
        log_file,
        maxBytes=10 * 1024 * 1024,  # 10 MB per file
        backupCount=5,
        encoding="utf-8",
    )
    _file_handler.setLevel(logging.INFO)
    _file_handler.setFormatter(formatter or logging.Formatter(LOG_FORMAT))
    return _file_handler


def is_console_handler(h: logging.Handler) -> bool:
    """Identifies the application console StreamHandler (excluding FileHandlers and CloudLoggingHandlers)."""
    if getattr(h, "name", None) == "ticketradar_console":
        return True
    return type(h) is logging.StreamHandler and getattr(h, "stream", None) in (sys.stdout, sys.stderr)


def configure_logging(enable_atatus_file_correlation: bool = False) -> None:
    """
    Configures centralized logging for the application:
    - Root Console StreamHandler: Clean, standard format WITHOUT Atatus correlation tags.
    - Root File Handler: Located in logs/ directory in src/Backend, formatted with AtatusFormatter
      when Atatus APM is active for log-trace correlation.
    - Google Cloud Logging: Attaches CloudLoggingHandler to root logger if credentials are configured.
    - Prevents redundant/duplicate logs in console by ensuring only a single console handler
      and suppressing duplicate uvicorn access logs.
    """
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)

    # 1. Ensure a single console handler on the root logger with clean standard formatting
    console_handlers = [h for h in root_logger.handlers if is_console_handler(h)]
    if console_handlers:
        console_handler = console_handlers[0]
        console_handler.name = "ticketradar_console"
        # Clean standard formatter for console (never AtatusFormatter)
        console_handler.setFormatter(logging.Formatter(LOG_FORMAT))
        # Remove any extra duplicate console handlers
        for extra in console_handlers[1:]:
            root_logger.removeHandler(extra)
    else:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.name = "ticketradar_console"
        console_handler.setLevel(logging.INFO)
        console_handler.setFormatter(logging.Formatter(LOG_FORMAT))
        root_logger.addHandler(console_handler)

    # Ensure console handler never has LoggingFilter attached
    try:
        from atatus.handlers.logging import LoggingFilter
        for f in list(console_handler.filters):
            if isinstance(f, LoggingFilter):
                console_handler.removeFilter(f)
    except Exception:
        pass

    # 2. Configure File Handler in src/Backend/logs/ directory
    if enable_atatus_file_correlation:
        try:
            from atatus.handlers.logging import Formatter as AtatusFormatter, LoggingFilter
            fh = get_file_handler(AtatusFormatter(LOG_FORMAT))
            if not any(isinstance(f, LoggingFilter) for f in fh.filters):
                fh.addFilter(LoggingFilter())
        except Exception:
            fh = get_file_handler(logging.Formatter(LOG_FORMAT))
    else:
        fh = get_file_handler(logging.Formatter(LOG_FORMAT))
        try:
            from atatus.handlers.logging import LoggingFilter
            for f in list(fh.filters):
                if isinstance(f, LoggingFilter):
                    fh.removeFilter(f)
        except Exception:
            pass

    if fh not in root_logger.handlers:
        root_logger.addHandler(fh)

    # 3. Attach Google Cloud Logging to root logger if available
    try:
        from ..services.gcp_logger import gcp_logger
        # gcp_logger automatically attaches CloudLoggingHandler to root_logger if enabled
    except Exception:
        pass

    # 4. Remove any duplicate handlers on child loggers so they propagate to root cleanly
    tr_logger = logging.getLogger("ticketradar")
    tr_logger.handlers.clear()
    tr_logger.propagate = True

    tr_api_logger = logging.getLogger("ticketradar.api")
    tr_api_logger.handlers.clear()
    tr_api_logger.propagate = True

    # 5. Silence duplicate uvicorn.access logs in console
    uvicorn_access = logging.getLogger("uvicorn.access")
    uvicorn_access.handlers.clear()
    uvicorn_access.propagate = False


def setup_logger(name: str = "ticketradar") -> logging.Logger:
    """Sets up an application logger that propagates to the root logger without duplicate handlers."""
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)
    logger.handlers.clear()
    logger.propagate = True
    return logger


# Main application logger
app_logger = setup_logger()


def get_job_logger(job_id: str) -> logging.Logger:
    """
    Creates or retrieves a job-specific logger.
    Propagates to root logger for both console and file logging.
    """
    logger = logging.getLogger(f"job.{job_id}")
    logger.setLevel(logging.INFO)
    logger.handlers.clear()
    logger.propagate = True
    return logger
