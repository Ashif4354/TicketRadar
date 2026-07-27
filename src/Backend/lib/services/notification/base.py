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
        Send a notification containing movie details and theatre availability.
        
        Parameters:
            subject (str): The notification subject.
            movie_name (str): The movie name.
            date_str (str): The target date in YYYYMMDD format.
            available_theatres (List[str]): Theatres where booking is open.
            unavailable_theatres (List[str]): Theatres where booking is unavailable.
            url (str): The movie booking URL.
            language (str): The notification language.
            format_name (str): The movie format.
        
        Returns:
            tuple[bool, str]: A tuple containing the delivery result and status message.
        """
        pass
