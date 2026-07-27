# src/core/job.py

import re
import urllib
import uuid
from datetime import datetime, timezone
import threading
from typing import Dict, List, Optional, Any

def _parse_movie_name_from_url(url: str, params: Optional[Dict[str, Any]] = None) -> str:
    """
    Extracts and formats a human-readable movie title from a BookMyShow URL.
    Example: 'https://in.bookmyshow.com/movies/chennai/the-odyssey-imax-2d/buytickets/ET00480917/20260730' -> 'The Odyssey'
    """
    if not url:
        return "BookMyShow Movie"

    try:
        # Match pattern: /movies/{city}/{movie_slug}/buytickets/...
        match = re.search(r"/movies/[^/]+/([^/]+)/buytickets", url, re.IGNORECASE)
        if not match:
            # Fallback: match /movies/{movie_slug}/ or raw slug in path
            match = re.search(r"/movies/([^/]+)", url, re.IGNORECASE)

        if match:
            slug = match.group(1).lower()
            # Clean common format suffixes from slug
            format_suffixes = [
                "-imax-3d", "-imax-2d", "-imax",
                "-4dx-3d", "-4dx", "-screenx", "-epiq",
                "-3d", "-2d"
            ]
            for fmt in format_suffixes:
                if slug.endswith(fmt):
                    slug = slug[:-len(fmt)]
                    break

            # Replace hyphens with spaces and capitalize each word
            words = slug.split("-")
            clean_title = " ".join(w.capitalize() for w in words if w)
            if clean_title:
                return clean_title
    except Exception:
        pass

    return "BookMyShow Movie"

class MonitorJob:
    """
    Domain model representing a single movie ticket monitoring job.
    Uses thread-safe state modifications via an internal Lock.
    Supports dynamic parameter maps.
    """

    def __init__(
        self,
        params: Dict[str, Any],
        notification_medium: str,
        notification_config: Dict[str, Any],
        service_provider: str = "bookmyshow",
        check_interval: Optional[int] = None,
        job_id: Optional[str] = None,
        created_by: Optional[str] = None,
        creator_email: Optional[str] = None
    ):
        self.id = job_id or str(uuid.uuid4())[:8]  # Short, readable ID
        self.params = params
        self.notification_medium = notification_medium.strip().lower()
        self.notification_config = notification_config
        self.service_provider = service_provider.strip().lower()
        self.check_interval = max(60, check_interval) if check_interval is not None else 60
        
        parsed = _parse_movie_name_from_url(params.get("url", ""), params)
        self.movie_name = parsed if parsed != "BookMyShow Movie" else "Fetching..."

        self.created_by = created_by
        self.creator_email = creator_email
        
        self.created_at = datetime.now(timezone.utc)
        self.status = "Idle"  # Idle, Running, Success, Error, Stopped
        self.last_checked_at: Optional[datetime] = None
        self.last_result: str = "Created"
        
        # Thread lock for state modifications
        self._lock = threading.Lock()

    @property
    def url(self) -> str:
        """Compatibility helper to retrieve URL from params."""
        return self.params.get("url", "")

    @property
    def date_str(self) -> str:
        """Compatibility helper to retrieve date_str from params."""
        return self.params.get("date_str", "")

    @property
    def theatres(self) -> List[str]:
        """Compatibility helper to retrieve theatres list from params."""
        raw_theatres = self.params.get("theatres", [])
        if isinstance(raw_theatres, str):
            return [t.strip() for t in raw_theatres.split("\n") if t.strip()]
        return [str(t).strip() for t in raw_theatres if str(t).strip()]

    @property
    def language(self) -> str:
        """Helper to retrieve language from params or URL query."""
        lang = self.params.get("language")
        if lang:
            return str(lang).capitalize()
        match = re.search(r"language=([^&]+)", self.url, re.IGNORECASE)
        if match:
            return urllib.parse.unquote(match.group(1)).capitalize()
        if self.service_provider.lower() == "bookmyshow":
            return "English"
        return ""

    @property
    def format_name(self) -> str:
        """Helper to retrieve format (e.g. 2D, 3D, IMAX 2D) from params or URL slug."""
        fmt = self.params.get("format")
        if fmt:
            return str(fmt)
        url_lower = self.url.lower()
        if "imax-3d" in url_lower or "imax 3d" in url_lower:
            return "IMAX 3D"
        if "imax-2d" in url_lower or "imax 2d" in url_lower or "imax" in url_lower:
            return "IMAX 2D"
        if "4dx-3d" in url_lower or "4dx 3d" in url_lower:
            return "4DX 3D"
        if "4dx" in url_lower:
            return "4DX"
        if "3d" in url_lower:
            return "3D"
        if "screenx" in url_lower:
            return "ScreenX"
        if "epiq" in url_lower:
            return "EPIQ"
        if self.service_provider.lower() == "bookmyshow":
            return "2D"
        return ""

    def update_state(self, status: str, last_result: str, movie_name: Optional[str] = None) -> None:
        """Thread-safely updates the state of the job in memory."""
        with self._lock:
            self.status = status
            self.last_result = last_result
            self.last_checked_at = datetime.now(timezone.utc)
            if movie_name:
                self.movie_name = movie_name

    def update_data(
        self,
        params: Dict[str, Any],
        notification_medium: str,
        notification_config: Dict[str, Any],
        service_provider: str = "bookmyshow",
        check_interval: Optional[int] = None
    ) -> None:
        """Thread-safely updates the job configuration and parameters."""
        with self._lock:
            self.params = params
            self.notification_medium = notification_medium.strip().lower()
            self.notification_config = notification_config
            self.service_provider = service_provider.strip().lower()
            self.check_interval = max(60, check_interval) if check_interval is not None else 60
            parsed_name = _parse_movie_name_from_url(params.get("url", ""), params)
            if parsed_name != "BookMyShow Movie":
                self.movie_name = parsed_name
            elif self.movie_name == "Fetching...":
                self.movie_name = "Fetching..."

    def get_state(self) -> Dict[str, Any]:
        """Thread-safely returns a full snapshot of the job state for API responses."""
        with self._lock:
            return {
                "id": self.id,
                "params": self.params,
                "url": self.url,
                "movie_name": self.movie_name,
                "date_str": self.date_str,
                "theatres": self.theatres,
                "language": self.language,
                "format": self.format_name,
                "service_provider": self.service_provider,
                "notification_medium": self.notification_medium,
                "notification_config": self.notification_config,
                "check_interval": self.check_interval,
                "created_at": self.created_at,
                "status": self.status,
                "last_checked_at": self.last_checked_at,
                "last_result": self.last_result,
                "created_by": self.created_by,
                "creator_email": self.creator_email,
            }

    def to_dict(self) -> Dict[str, Any]:
        """
        Serializes essential job metadata to a Firestore-compatible dictionary.
        Note: last_result and last_checked_at are omitted to prevent unnecessary cloud costs.
        """
        with self._lock:
            return {
                "id": self.id,
                "params": self.params,
                "service_provider": self.service_provider,
                "notification_medium": self.notification_medium,
                "notification_config": self.notification_config,
                "check_interval": self.check_interval,
                "movie_name": self.movie_name,
                "language": self.language,
                "format": self.format_name,
                "created_by": self.created_by,
                "creator_email": self.creator_email,
                "status": self.status,
                "created_at": self.created_at.isoformat() if isinstance(self.created_at, datetime) else self.created_at,
            }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "MonitorJob":
        """Deserializes a dictionary (e.g. from Firestore) into a MonitorJob instance."""
        job = cls(
            params=data.get("params", {}),
            notification_medium=data.get("notification_medium", "email"),
            notification_config=data.get("notification_config", {}),
            service_provider=data.get("service_provider", "bookmyshow"),
            check_interval=data.get("check_interval", 30),
            job_id=data.get("id"),
            created_by=data.get("created_by"),
            creator_email=data.get("creator_email")
        )
        job.movie_name = data.get("movie_name", "Fetching...")
        job.status = data.get("status", "Idle")
        job.last_result = data.get("last_result", "Created")

        created_at_val = data.get("created_at")
        if isinstance(created_at_val, str):
            try:
                job.created_at = datetime.fromisoformat(created_at_val)
            except ValueError:
                pass
        elif isinstance(created_at_val, datetime):
            job.created_at = created_at_val

        last_checked_val = data.get("last_checked_at")
        if isinstance(last_checked_val, str):
            try:
                job.last_checked_at = datetime.fromisoformat(last_checked_val)
            except ValueError:
                pass
        elif isinstance(last_checked_val, datetime):
            job.last_checked_at = last_checked_val

        return job

