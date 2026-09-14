# src/Backend/lib/services/notification/admin_notifier.py

import logging
from typing import List, Optional, Dict, Any
from datetime import datetime, timezone
from ...utils.config import settings
from .DiscordEmbed import DiscordEmbed

logger = logging.getLogger("ticketradar.admin_notifier")

DEFAULT_AVATAR = "https://cdn-icons-png.flaticon.com/512/847/847969.png"

async def send_admin_discord_embed(
    title: str,
    description: str,
    color: int,
    fields: Optional[List[Dict[str, Any]]] = None,
    thumbnail_url: Optional[str] = None
) -> tuple[bool, str]:
    """
    Sends a formatted embed notification to ADMIN_DISCORD_WEBHOOK_URL.
    """
    webhook_url = getattr(settings, "admin_discord_webhook_url", "") if settings else ""
    return await DiscordEmbed.send_embed(
        webhook_url=webhook_url,
        title=title,
        description=description,
        color=color,
        fields=fields,
        thumbnail_url=thumbnail_url,
        footer_text="TicketRadar Admin Alerts"
    )


# 1. New User Registered and First Login
async def notify_first_login(user_name: str, email: str, photo_url: Optional[str] = None):
    title = "👤 New User Registered & First Login"
    description = f"User **{user_name or 'N/A'}** has registered and logged in for the first time."
    color = 0x10B981  # Emerald Green
    fields = [
        {"name": "User Name", "value": user_name or "N/A", "inline": True},
        {"name": "Email", "value": email or "N/A", "inline": True},
    ]
    await send_admin_discord_embed(title, description, color, fields, photo_url)


# 2. Access Request Created
async def notify_access_request_created(user_name: str, email: str, photo_url: Optional[str] = None):
    title = "📥 New Access Request Created"
    description = f"A new access request has been submitted by **{user_name or 'N/A'}**."
    color = 0xF59E0B  # Amber/Yellow
    fields = [
        {"name": "User Name", "value": user_name or "N/A", "inline": True},
        {"name": "Email", "value": email or "N/A", "inline": True},
        {"name": "Status", "value": "Pending Approval", "inline": False},
    ]
    await send_admin_discord_embed(title, description, color, fields, photo_url)


# 3. Access Request Approved or Denied
async def notify_access_request_status(user_name: str, email: str, status: str, photo_url: Optional[str] = None):
    is_approved = status.lower() == "approved"
    icon = "✅" if is_approved else "❌"
    action_text = "Approved" if is_approved else "Denied"
    color = 0x10B981 if is_approved else 0xEF4444

    title = f"{icon} Access Request {action_text}"
    description = f"User access request for **{user_name or 'N/A'}** was **{action_text.lower()}**."
    fields = [
        {"name": "User Name", "value": user_name or "N/A", "inline": True},
        {"name": "Email", "value": email or "N/A", "inline": True},
        {"name": "Decision", "value": action_text, "inline": True},
    ]
    await send_admin_discord_embed(title, description, color, fields, photo_url)


# 4. User Blocked or Unblocked
async def notify_user_block_status(user_name: str, email: str, is_blocked: bool, photo_url: Optional[str] = None):
    icon = "🚫" if is_blocked else "🔓"
    action_text = "Blocked" if is_blocked else "Unblocked"
    color = 0xDC2626 if is_blocked else 0x8B5CF6

    title = f"{icon} User {action_text}"
    description = f"User **{user_name or 'N/A'}** has been **{action_text.lower()}**."
    fields = [
        {"name": "User Name", "value": user_name or "N/A", "inline": True},
        {"name": "Email", "value": email or "N/A", "inline": True},
        {"name": "Status", "value": action_text, "inline": True},
    ]
    await send_admin_discord_embed(title, description, color, fields, photo_url)


# Helper to format theatre list cleanly
def _format_theatres(theatres: List[str]) -> str:
    if not theatres:
        return "None"
    if len(theatres) <= 3:
        return "\n".join([f"• {t}" for t in theatres])
    return "\n".join([f"• {t}" for t in theatres[:3]]) + f"\n*...and {len(theatres) - 3} more*"


# 5. New Job Created
async def notify_job_created(
    job_id: str,
    movie_name: str,
    user_name: str,
    email: str,
    booking_platform: str,
    theatres: List[str],
    date_str: str
):
    title = "🚀 New Job Created"
    description = f"A new monitoring job **#{job_id}** was created by **{user_name or 'N/A'}**."
    color = 0x3B82F6  # Blue
    fields = [
        {"name": "Job ID", "value": job_id, "inline": True},
        {"name": "Movie Name", "value": movie_name or "N/A", "inline": True},
        {"name": "Date", "value": date_str or "N/A", "inline": True},
        {"name": "User Name", "value": user_name or "N/A", "inline": True},
        {"name": "Email", "value": email or "N/A", "inline": True},
        {"name": "Booking Platform", "value": booking_platform or "N/A", "inline": True},
        {"name": "Theatres List", "value": _format_theatres(theatres), "inline": False},
    ]
    await send_admin_discord_embed(title, description, color, fields)


# 6. Job Stopped (by User)
async def notify_job_stopped(
    job_id: str,
    movie_name: str,
    user_name: str,
    email: str,
    booking_platform: str,
    theatres: List[str],
    date_str: str
):
    title = "⏸️ Job Stopped"
    description = f"Monitoring job **#{job_id}** was stopped by user **{user_name or 'N/A'}**."
    color = 0xF97316  # Orange
    fields = [
        {"name": "Job ID", "value": job_id, "inline": True},
        {"name": "Movie Name", "value": movie_name or "N/A", "inline": True},
        {"name": "Date", "value": date_str or "N/A", "inline": True},
        {"name": "User Name", "value": user_name or "N/A", "inline": True},
        {"name": "Email", "value": email or "N/A", "inline": True},
        {"name": "Booking Platform", "value": booking_platform or "N/A", "inline": True},
        {"name": "Theatres List", "value": _format_theatres(theatres), "inline": False},
    ]
    await send_admin_discord_embed(title, description, color, fields)


# 7. Job Deleted (by User)
async def notify_job_deleted(
    job_id: str,
    movie_name: str,
    user_name: str,
    email: str,
    booking_platform: str,
    theatres: List[str],
    date_str: str
):
    title = "🗑️ Job Deleted"
    description = f"Monitoring job **#{job_id}** was deleted by user **{user_name or 'N/A'}**."
    color = 0x6B7280  # Grey
    fields = [
        {"name": "Job ID", "value": job_id, "inline": True},
        {"name": "Movie Name", "value": movie_name or "N/A", "inline": True},
        {"name": "Date", "value": date_str or "N/A", "inline": True},
        {"name": "User Name", "value": user_name or "N/A", "inline": True},
        {"name": "Email", "value": email or "N/A", "inline": True},
        {"name": "Booking Platform", "value": booking_platform or "N/A", "inline": True},
        {"name": "Theatres List", "value": _format_theatres(theatres), "inline": False},
    ]
    await send_admin_discord_embed(title, description, color, fields)


# 8. Job Deleted / Stopped / Started by Admin
async def notify_job_admin_action(
    action: str,  # "stopped", "deleted", or "started"
    job_id: str,
    movie_name: str,
    owner_user_name: str,
    owner_email: str,
    booking_platform: str,
    theatres: List[str],
    date_str: str,
    admin_name: str,
    admin_email: str
):
    action_clean = action.capitalize()
    is_started = action.lower() == "started"
    icon = "▶️" if is_started else "🛡️"
    title = f"{icon} Job {action_clean} by Admin"
    description = f"Monitoring job **#{job_id}** was **{action.lower()}** by administrator **{admin_name or 'N/A'}**."
    color = 0x10B981 if is_started else 0x7C3AED
    fields = [
        {"name": "Job ID", "value": job_id, "inline": True},
        {"name": "Movie Name", "value": movie_name or "N/A", "inline": True},
        {"name": "Date", "value": date_str or "N/A", "inline": True},
        {"name": "Job Owner", "value": f"{owner_user_name or 'N/A'} ({owner_email or 'N/A'})", "inline": True},
        {"name": "Action By (Admin)", "value": f"{admin_name or 'N/A'} ({admin_email or 'N/A'})", "inline": True},
        {"name": "Booking Platform", "value": booking_platform or "N/A", "inline": True},
        {"name": "Theatres List", "value": _format_theatres(theatres), "inline": False},
    ]
    if is_started:
        fields.insert(5, {"name": "User Charged", "value": "No (Admin Action)", "inline": True})

    await send_admin_discord_embed(title, description, color, fields)


# 9. New Admin Created
async def notify_new_admin_created(user_name: str, email: str, photo_url: Optional[str] = None):
    title = "👑 New Admin Created"
    description = f"User **{user_name or 'N/A'}** has been assigned administrator privileges."
    color = 0xEAB308  # Gold / Yellow
    fields = [
        {"name": "Admin Name", "value": user_name or "N/A", "inline": True},
        {"name": "Email", "value": email or "N/A", "inline": True},
        {"name": "Role", "value": "Admin", "inline": True},
    ]
    await send_admin_discord_embed(title, description, color, fields, photo_url)
