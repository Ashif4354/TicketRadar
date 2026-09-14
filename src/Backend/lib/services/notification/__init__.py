from .base import NotificationStrategy
from .email_strategy import EmailNotificationStrategy
from .discord_strategy import DiscordWebhookNotificationStrategy
from .factory import NotificationStrategyFactory
from .user_mailer import send_user_access_granted_email
from .templates.email import EmailTemplates
from .templates.message import MessageTemplates
from .templates.discord import DiscordTemplates

__all__ = [
    "NotificationStrategy",
    "EmailNotificationStrategy",
    "DiscordWebhookNotificationStrategy",
    "NotificationStrategyFactory",
    "send_user_access_granted_email",
    "EmailTemplates",
    "MessageTemplates",
    "DiscordTemplates",
]
