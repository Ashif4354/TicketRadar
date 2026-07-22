# src/core/job.py

import uuid
from datetime import datetime
import threading
from typing import Dict, List, Optional, Any

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
        created_by: Optional[str] = None
    ):
        self.id = job_id or str(uuid.uuid4())[:8]  # Short, readable ID
        self.params = params
        self.notification_medium = notification_medium.strip().lower()
        self.notification_config = notification_config
        self.service_provider = service_provider.strip().lower()
        self.check_interval = max(30, check_interval) if check_interval is not None else 30
        self.movie_name = "Fetching..."
        self.created_by = created_by
        
        self.created_at = datetime.now()
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

    def update_state(self, status: str, last_result: str, movie_name: Optional[str] = None) -> None:
        """Thread-safely updates the state of the job."""
        with self._lock:
            self.status = status
            self.last_result = last_result
            self.last_checked_at = datetime.now()
            if movie_name:
                self.movie_name = movie_name

    def get_state(self) -> Dict[str, Any]:
        """Thread-safely returns a snapshot of the job state."""
        with self._lock:
            return {
                "id": self.id,
                "params": self.params,
                "url": self.url,
                "movie_name": self.movie_name,
                "date_str": self.date_str,
                "theatres": self.theatres,
                "service_provider": self.service_provider,
                "notification_medium": self.notification_medium,
                "notification_config": self.notification_config,
                "check_interval": self.check_interval,
                "created_at": self.created_at,
                "status": self.status,
                "last_checked_at": self.last_checked_at,
                "last_result": self.last_result,
                "created_by": self.created_by,
            }
