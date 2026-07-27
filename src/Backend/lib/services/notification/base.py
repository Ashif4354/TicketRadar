# src/services/notification/base.py

from abc import ABC, abstractmethod
from typing import List

class NotificationStrategy(ABC):
    """
    Abstract base class representing an asynchronous notification delivery strategy.
    """

    @abstractmethod
    async def send_notification(
        self,
        subject: str,
        movie_name: str,
        date_str: str,
        available_theatres: List[str],
        unavailable_theatres: List[str],
        url: str,
        language: str = "",
        format_name: str = ""
    ) -> tuple[bool, str]:
        """
        Asynchronously sends a notification with structured theatre availability.
        
        Args:
            subject (str): The subject of the notification.
            movie_name (str): The name of the movie.
            date_str (str): The target date (YYYYMMDD).
            available_theatres (List[str]): List of theatres where booking is open.
            unavailable_theatres (List[str]): List of theatres where booking is not yet open.
            url (str): The movie booking URL.
            language (str): Optional movie language (e.g. "English", "Hindi").
            format_name (str): Optional movie format (e.g. "2D", "3D", "IMAX 2D").
            
        Returns:
            tuple[bool, str]: A tuple of (success_boolean, status_message).
        """
        pass
