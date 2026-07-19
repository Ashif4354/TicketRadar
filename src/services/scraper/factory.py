# src/services/scraper/factory.py

from typing import Type
from src.services.scraper.providers.base import BookingChecker

class ScraperFactory:
    """
    Factory class to instantiate booking checkers based on service provider name.
    """

    @staticmethod
    def get_scraper_class(provider_name: str) -> Type[BookingChecker]:
        """
        Resolves and returns the scraper class for the given provider name.
        
        Args:
            provider_name (str): The name of the service provider (e.g. 'bookmyshow').
            
        Returns:
            Type[BookingChecker]: The BookingChecker class type itself.
            
        Raises:
            ValueError: If the provider name is not supported.
        """
        provider_clean = provider_name.strip().lower()
        if provider_clean == "bookmyshow":
            from src.services.scraper.providers.bookmyshow import BookMyShowBookingChecker
            return BookMyShowBookingChecker
        else:
            raise ValueError(f"Unknown service provider: {provider_name}")

    @staticmethod
    def create_scraper(provider_name: str) -> BookingChecker:
        """
        Creates and returns a concrete scraper instance for the given provider.
        
        Args:
            provider_name (str): The name of the service provider (e.g. 'bookmyshow').
            
        Returns:
            BookingChecker: An instance of a concrete BookingChecker subclass.
        """
        scraper_cls = ScraperFactory.get_scraper_class(provider_name)
        return scraper_cls()
