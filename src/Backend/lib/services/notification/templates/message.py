# src/Backend/lib/services/notification/templates/message.py

from typing import Dict, Any, List, Optional


class MessageTemplates:
    """
    Centralized message template catalog for SMS and WhatsApp notifications.
    Provides get_template function returning body text and structured template variables.
    Can be inherited by SMSNotificationStrategy and WhatsAppNotificationStrategy.
    """

    @classmethod
    def get_template(cls, template_name: str, **context: Any) -> Dict[str, Any]:
        """
        Retrieves and renders a message template for SMS and WhatsApp.

        Args:
            template_name: The identifier of the template.
            **context: Context variables.

        Returns:
            Dict containing 'body' (formatted text) and 'variables' (for WhatsApp template mapping).
        """
        norm_name = template_name.strip().lower().replace("-", "_")

        renderers = {
            "booking_alert": cls._render_booking_alert,
            "alert": cls._render_booking_alert,
            "call_unanswered": cls._render_call_unanswered,
            "call_retry": cls._render_call_unanswered,
            "call_3x_unanswered": cls._render_call_unanswered,
            "call_success": cls._render_call_success,
            "job_created": cls._render_job_created,
            "job_cancelled": cls._render_job_cancelled,
            "wallet_topup": cls._render_wallet_topup,
            "wallet_topup_success": cls._render_wallet_topup,
            "wallet_debit": cls._render_wallet_topup,
            "refund": cls._render_refund,
            "notification_failed": cls._render_notification_failed,
        }

        renderer = renderers.get(norm_name)
        if not renderer:
            # Generic fallback
            body = context.get("body") or f"TicketRadar: {template_name}"
            return {"body": body, "variables": context}

        return renderer(**context)

    @classmethod
    def _render_booking_alert(
        cls,
        movie_name: str = "Movie",
        date_str: str = "",
        available_theatres: Optional[List[str]] = None,
        unavailable_theatres: Optional[List[str]] = None,
        url: str = "",
        language: str = "",
        format_name: str = "",
        **kwargs: Any
    ) -> Dict[str, Any]:
        theatres = available_theatres or ([kwargs["cinema_name"]] if "cinema_name" in kwargs else [])
        booking_url = url or kwargs.get("booking_url", "")
        theatres_summary = ", ".join(theatres[:3])
        if len(theatres) > 3:
            theatres_summary += f" +{len(theatres)-3} more"

        details = " | ".join(filter(None, [language, format_name]))
        details_str = f" ({details})" if details else ""

        body = (
            f"🎬 TicketRadar Alert! Booking is now open for *{movie_name}*{details_str} on *{date_str}* "
            f"at {theatres_summary}. Book tickets now: {booking_url}"
        )

        variables = {
            "1": movie_name,
            "2": f"{date_str} at {theatres_summary}",
            "3": booking_url,
        }

        return {"body": body, "variables": variables}

    @classmethod
    def _render_call_unanswered(
        cls,
        phone_number: str = "",
        movie_name: str = "",
        date_str: str = "",
        url: str = "",
        **kwargs: Any
    ) -> Dict[str, Any]:
        attempts = kwargs.get("attempts", 3)
        booking_url = url or kwargs.get("booking_url", "")
        body = (
            f"TicketRadar Notice: We attempted to call {phone_number} {attempts} times regarding {movie_name} ({date_str}). "
            f"Tickets are open! Book now: {booking_url}"
        )
        return {"body": body, "variables": {"movie_name": movie_name, "date_str": date_str, "url": booking_url}}

    @classmethod
    def _render_call_success(
        cls,
        movie_name: str = "",
        date_str: str = "",
        url: str = "",
        **kwargs: Any
    ) -> Dict[str, Any]:
        body = (
            f"TicketRadar: Voice alert delivered for {movie_name} ({date_str}). "
            f"Confirm your seats now: {url}"
        )
        return {"body": body, "variables": {"movie_name": movie_name, "date_str": date_str, "url": url}}

    @classmethod
    def _render_job_created(
        cls,
        movie_name: str = "",
        date_str: str = "",
        job_id: str = "",
        **kwargs: Any
    ) -> Dict[str, Any]:
        body = f"TicketRadar: Tracker #{job_id} active for {movie_name} on {date_str}. We will notify you instantly."
        return {"body": body, "variables": {"movie_name": movie_name, "date_str": date_str, "job_id": job_id}}

    @classmethod
    def _render_job_cancelled(
        cls,
        movie_name: str = "",
        job_id: str = "",
        refund_inr: float = 0.0,
        **kwargs: Any
    ) -> Dict[str, Any]:
        ref_text = f" Refund: ₹{refund_inr:.2f}." if refund_inr > 0 else ""
        body = f"TicketRadar: Tracker #{job_id} for {movie_name} has been cancelled.{ref_text}"
        return {"body": body, "variables": {"movie_name": movie_name, "job_id": job_id}}

    @classmethod
    def _render_wallet_topup(
        cls,
        amount_inr: float = 0.0,
        balance_inr: float = 0.0,
        **kwargs: Any
    ) -> Dict[str, Any]:
        body = f"TicketRadar: ₹{amount_inr:.2f} added to your wallet. Balance: ₹{balance_inr:.2f}."
        return {"body": body, "variables": {"amount_inr": str(amount_inr), "balance_inr": str(balance_inr)}}

    @classmethod
    def _render_refund(
        cls,
        amount_inr: float = 0.0,
        reason: str = "",
        balance_inr: float = 0.0,
        **kwargs: Any
    ) -> Dict[str, Any]:
        body = f"TicketRadar: ₹{amount_inr:.2f} refunded to your wallet. Reason: {reason}. Balance: ₹{balance_inr:.2f}."
        return {"body": body, "variables": {"amount_inr": str(amount_inr), "reason": reason}}

    @classmethod
    def _render_notification_failed(
        cls,
        movie_name: str = "",
        job_id: str = "",
        **kwargs: Any
    ) -> Dict[str, Any]:
        body = f"TicketRadar: Alert delivery failed for {movie_name} (#{job_id}). Fee has been refunded to your wallet."
        return {"body": body, "variables": {"movie_name": movie_name, "job_id": job_id}}
