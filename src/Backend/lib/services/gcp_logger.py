# src/Backend/lib/services/gcp_logger.py

import os
import logging
import traceback
from datetime import datetime, timezone
from typing import Dict, Any, Optional

from ..utils.config import settings

# Module logger for fallback/local logging
logger = logging.getLogger("ticketradar.gcp_logger")

class FrameworkLogFilter(logging.Filter):
    """
    Filter to suppress uvicorn and fastapi INFO-level log records from Google Cloud Logging.
    WARNING, ERROR, and CRITICAL logs from any source are allowed.
    """
    def filter(self, record: logging.LogRecord) -> bool:
        logger_name = record.name.lower()
        if record.levelno <= logging.INFO:
            if "uvicorn" in logger_name or "fastapi" in logger_name:
                return False
        return True

class GCPLoggingService:
    """
    Singleton service managing Google Cloud Logging integration.
    Handles structured domain audit logs and attaches CloudLoggingHandler for system warnings/errors.
    """
    _instance = None

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super(GCPLoggingService, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if getattr(self, "_initialized", False):
            return
        self._initialized = True
        self.client = None
        self.gcp_logger = None
        self.is_enabled = False
        self._init_client()

    def _init_client(self):
        if not settings:
            logger.warning("Settings not available. GCP Logging disabled.")
            return

        cred_dict = {
            "type": settings.gcp_logging_type or "service_account",
            "project_id": settings.gcp_logging_project_id,
            "private_key_id": settings.gcp_logging_private_key_id,
            "private_key": settings.gcp_logging_private_key.replace("\\n", "\n") if settings.gcp_logging_private_key else "",
            "client_email": settings.gcp_logging_client_email,
            "client_id": settings.gcp_logging_client_id,
            "auth_uri": settings.gcp_logging_auth_uri or "https://accounts.google.com/o/oauth2/auth",
            "token_uri": settings.gcp_logging_token_uri or "https://oauth2.googleapis.com/token",
            "auth_provider_x509_cert_url": settings.gcp_logging_auth_provider_x509_cert_url or "https://www.googleapis.com/oauth2/v1/certs",
            "client_x509_cert_url": settings.gcp_logging_client_x509_cert_url,
            "universe_domain": getattr(settings, "gcp_logging_universe_domain", "googleapis.com") or "googleapis.com"
        }

        if not cred_dict["project_id"] or not cred_dict["private_key"]:
            logger.warning("GCP Logging credentials missing in environment settings. GCP Logging disabled.")
            return

        try:
            import google.cloud.logging
            from google.cloud.logging.handlers import CloudLoggingHandler

            self.client = google.cloud.logging.Client.from_service_account_info(cred_dict)
            self.gcp_logger = self.client.logger("ticketradar-server")
            self.is_enabled = True
            logger.info(f"Google Cloud Logging initialized successfully for project: {cred_dict['project_id']}")

            # Attach CloudLoggingHandler to root python logger with framework filter
            handler = CloudLoggingHandler(self.client, name="ticketradar-system-logs")
            handler.addFilter(FrameworkLogFilter())
            handler.setLevel(logging.INFO)  # Suppresses uvicorn/fastapi INFO via filter, passes application file loggers & warning+
            
            root_logger = logging.getLogger()
            root_logger.addHandler(handler)

        except Exception as e:
            logger.error(f"Failed to initialize Google Cloud Logging: {e}")
            self.is_enabled = False

    def log_event(
        self,
        action: str,
        user_id: Optional[str] = "system",
        details: Optional[Dict[str, Any]] = None,
        level: str = "INFO",
        request: Optional[Any] = None,
        exception: Optional[Exception] = None
    ) -> Dict[str, Any]:
        """
        Logs a structured domain audit event to Google Cloud Logging.

        Payload schema:
        - timestamp: ISO 8601 UTC timestamp
        - user_id: Authenticated user UID or 'system' / 'unauthenticated'
        - action: Action description (e.g. "Job Created", "User Blocked")
        - details: Contextual event data dictionary
        - metadata: Request details, severity, service info
        """
        timestamp = datetime.now(timezone.utc).isoformat()
        event_details = details if details is not None else {}

        if exception:
            event_details["error"] = str(exception)
            event_details["traceback"] = traceback.format_exc()

        metadata: Dict[str, Any] = {
            "service": "ticketradar-backend",
            "severity": level.upper()
        }

        if request:
            try:
                metadata["endpoint"] = str(request.url)
                metadata["method"] = request.method
                if hasattr(request, "client") and request.client:
                    metadata["client_ip"] = request.client.host
            except Exception as req_err:
                logger.debug(f"Failed to extract request metadata: {req_err}")

        payload = {
            "timestamp": timestamp,
            "user_id": user_id or "system",
            "action": action,
            "details": event_details,
            "metadata": metadata
        }

        # Send structured log to GCP Cloud Logging
        if self.is_enabled and self.gcp_logger:
            try:
                severity_map = {
                    "DEBUG": "DEBUG",
                    "INFO": "INFO",
                    "WARNING": "WARNING",
                    "ERROR": "ERROR",
                    "CRITICAL": "CRITICAL"
                }
                gcp_severity = severity_map.get(level.upper(), "INFO")
                self.gcp_logger.log_struct(payload, severity=gcp_severity)
            except Exception as e:
                logger.error(f"Failed to write struct log to GCP Cloud Logging: {e}")

        # Local fallback log string for stdout console
        log_msg = f"[GCP LOG EVENT] [{action}] user_id={payload['user_id']} details={event_details}"
        if level.upper() == "ERROR" or level.upper() == "CRITICAL":
            logger.error(log_msg)
        elif level.upper() == "WARNING":
            logger.warning(log_msg)
        else:
            logger.info(log_msg)

        return payload


# Singleton instance
gcp_logger = GCPLoggingService()
