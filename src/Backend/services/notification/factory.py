# src/services/notification/factory.py

from src.Backend.services.notification.base import NotificationStrategy
from src.Backend.services.notification.email_strategy import EmailNotificationStrategy
from src.Backend.services.notification.discord_strategy import DiscordWebhookNotificationStrategy

class NotificationStrategyFactory:
    """
    Factory pattern class to instantiate the correct NotificationStrategy based on configuration.
    """

    @staticmethod
    def create_strategy(medium: str, config: dict) -> NotificationStrategy:
        """
        Creates a notification strategy.
        
        Args:
            medium (str): Either 'email' or 'discord'.
            config (dict): Configuration options for the selected strategy.
                           Must contain 'recipient_email' for email or 'webhook_url' for discord.
        
        Returns:
            NotificationStrategy: An instance of a concrete strategy.
        """
        norm_medium = medium.strip().lower()
        if norm_medium == "email":
            email = config.get("recipient_email", "").strip()
            return EmailNotificationStrategy(email)
        elif norm_medium in ("discord", "discord webhook"):
            webhook_url = config.get("webhook_url", "").strip()
            return DiscordWebhookNotificationStrategy(webhook_url)
        else:
            raise ValueError(f"Unknown notification medium: {medium}. Supported types are 'email' or 'discord'")
