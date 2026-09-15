# src/Backend/lib/utils/apm.py

import os
import logging
from typing import Optional, Any
from contextlib import asynccontextmanager
from .config import settings

logger = logging.getLogger("ticketradar.apm")


def is_atatus_enabled() -> bool:
    """
    Checks whether Atatus APM is enabled with a valid non-empty license key
    and an active initialized client.
    """
    key = ""
    if settings and getattr(settings, "atatus_license_key", None):
        key = str(settings.atatus_license_key).strip()
    if not key:
        key = (os.getenv("ATATUS_LICENSE_KEY") or "").strip()
    if not key:
        return False
    try:
        import atatus
        return atatus.get_client() is not None
    except Exception:
        return False


def get_client() -> Any:
    """Returns the active Atatus client if enabled, otherwise None."""
    if not is_atatus_enabled():
        return None
    try:
        import atatus
        return atatus.get_client()
    except Exception:
        return None


def set_user(user_id: Optional[str] = None, username: Optional[str] = None, email: Optional[str] = None) -> None:
    """Sets user identity on the active Atatus transaction if enabled."""
    if not is_atatus_enabled():
        return
    try:
        import atatus
        kwargs = {}
        if user_id is not None:
            kwargs["user_id"] = str(user_id)
        if username is not None:
            kwargs["username"] = str(username)
        if email is not None:
            kwargs["email"] = str(email)
        atatus.set_user(**kwargs)
    except Exception:
        pass


def set_transaction_name(name: str) -> None:
    """Sets transaction name on active Atatus transaction if enabled."""
    if not is_atatus_enabled():
        return
    try:
        import atatus
        atatus.set_transaction_name(name)
    except Exception:
        pass


def set_transaction_outcome(outcome: str, **kwargs: Any) -> None:
    """Sets transaction outcome ('success' or 'failure') on active transaction if enabled."""
    if not is_atatus_enabled():
        return
    try:
        import atatus
        atatus.set_transaction_outcome(outcome, **kwargs)
    except Exception:
        pass


def capture_exception(exc: Optional[Exception] = None, **kwargs: Any) -> None:
    """Captures exception to Atatus if enabled."""
    if not is_atatus_enabled():
        return
    try:
        import sys
        import atatus
        client = atatus.get_client()
        if client is not None:
            if exc is not None:
                exc_info = (type(exc), exc, exc.__traceback__)
            else:
                exc_info = sys.exc_info()
            client.capture_exception(exc_info=exc_info, **kwargs)
    except Exception:
        pass


@asynccontextmanager
async def async_capture_span(name: str, span_type: str = "code.custom", labels: Optional[dict] = None, **kwargs: Any):
    """
    Async context manager that wraps a block in an Atatus span if enabled.
    Yields None and acts as a transparent no-op when Atatus is disabled or no license key is set.
    """
    if not is_atatus_enabled():
        yield None
        return

    try:
        import atatus
        async with atatus.async_capture_span(name, span_type=span_type, labels=labels, **kwargs) as span:
            yield span
    except Exception:
        yield None
