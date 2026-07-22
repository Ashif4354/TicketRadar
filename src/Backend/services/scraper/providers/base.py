# src/services/scraper/providers/base.py

from abc import ABC, abstractmethod
from typing import List, Tuple, Optional, Dict, Any

class BookingChecker(ABC):
    """
    Abstract base class representing an asynchronous ticket booking scraper service (Service Layer).
    Supports dynamic metadata mapping for customized service fields.
    """

    @classmethod
    @abstractmethod
    def get_required_fields(cls) -> Dict[str, Dict[str, Any]]:
        """
        Declares metadata about fields required by this scraper.
        Returns:
            Dict[str, Dict[str, Any]]: A mapping of field key to field metadata.
            Example:
            {
                "url": {
                    "type": "text",
                    "label": "URL Input",
                    "placeholder": "https://...",
                    "help": "Helpful hint text"
                }
            }
        """
        pass

    @abstractmethod
    async def check_booking(
        self,
        params: Dict[str, Any],
        **kwargs
    ) -> Tuple[bool, str, Optional[str], List[str], List[str]]:
        """
        Checks the specified service for date clickability and theatre availability.

        Args:
            params (Dict[str, Any]): Dictionary containing service-specific inputs.

        Returns:
            Tuple[bool, str, Optional[str], List[str], List[str]]: A tuple of:
                              - bool: True if the booking target is open and available, False otherwise.
                              - str: Description of the result.
                              - Optional[str]: Extracted movie name if found, else None.
                              - List[str]: List of available theatres.
                              - List[str]: List of unavailable theatres.
        """
        pass

    async def close(self) -> None:
        """
        Cleans up and closes any active resources (like Playwright browser/page objects).
        """
        pass
