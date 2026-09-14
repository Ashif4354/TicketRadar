# src/Backend/lib/services/notification/templates/__init__.py

from .email import EmailTemplates
from .message import MessageTemplates
from .discord import DiscordTemplates

__all__ = ["EmailTemplates", "MessageTemplates", "DiscordTemplates"]
