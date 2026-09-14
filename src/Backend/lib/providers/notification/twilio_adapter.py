# src/Backend/lib/providers/notification/twilio_adapter.py

import asyncio
import json
import logging
import urllib.parse
from typing import Dict, Any, Optional

from twilio.rest import Client
from twilio.base.exceptions import TwilioRestException
from twilio.request_validator import RequestValidator

from .base import NotificationProviderAdapter, ProviderMessageResult, ProviderCallResult
from ...utils.redact import redact_phone

logger = logging.getLogger("ticketradar.providers.twilio")

class TwilioProviderAdapter(NotificationProviderAdapter):
    """
    Concrete adapter for Twilio Programmable Messaging & Programmable Voice.
    Uses one unified phone number for SMS, Voice, and WhatsApp.
    """

    def __init__(
        self,
        account_sid: str,
        auth_token: str,
        from_number: str,
        whatsapp_content_sid: Optional[str] = None,
    ):
        self._account_sid = account_sid
        self._auth_token = auth_token
        self._from_number = from_number.strip() if from_number else ""
        self._whatsapp_from = f"whatsapp:{self._from_number}" if self._from_number and not self._from_number.startswith("whatsapp:") else self._from_number
        self._whatsapp_content_sid = whatsapp_content_sid or ""

        # Initialize Twilio Client and Validator if credentials provided
        if self._account_sid and self._auth_token:
            self._client = Client(self._account_sid, self._auth_token)
            self._validator = RequestValidator(self._auth_token)
        else:
            self._client = None
            self._validator = None

    def _get_client(self) -> Client:
        if not self._client:
            raise ValueError("Twilio credentials not configured (TWILIO_ACCOUNT_SID or TWILIO_AUTH_TOKEN missing).")
        return self._client

    async def send_sms(
        self,
        to: str,
        body: str,
        idempotency_key: str,
    ) -> ProviderMessageResult:
        """Send SMS via Twilio API asynchronously."""
        def _call_twilio():
            client = self._get_client()
            return client.messages.create(
                to=to,
                from_=self._from_number,
                body=body,
            )

        try:
            msg = await asyncio.to_thread(_call_twilio)
            logger.info(f"Twilio SMS dispatched. SID: {msg.sid}, to: {redact_phone(to)}")
            return ProviderMessageResult(
                success=True,
                provider_id=msg.sid,
            )
        except TwilioRestException as tre:
            logger.error(f"Twilio SMS Rest error: code={tre.code}, msg={tre.msg}, to={redact_phone(to)}")
            return ProviderMessageResult(
                success=False,
                provider_id="",
                error_code=str(tre.code),
                error_message=str(tre.msg),
            )
        except Exception as e:
            logger.error(f"Twilio SMS general error: {e}, to={redact_phone(to)}")
            return ProviderMessageResult(
                success=False,
                provider_id="",
                error_code="TWILIO_SEND_ERROR",
                error_message=str(e),
            )

    async def send_whatsapp_template(
        self,
        to: str,
        template_id: str,
        template_variables: Dict[str, Any],
        idempotency_key: str,
    ) -> ProviderMessageResult:
        """Send WhatsApp message using Twilio Content API or fallback template body."""
        target = f"whatsapp:{to}" if not to.startswith("whatsapp:") else to
        actual_template_id = template_id or self._whatsapp_content_sid

        def _call_twilio():
            client = self._get_client()
            if actual_template_id and actual_template_id.startswith("HX"):
                return client.messages.create(
                    to=target,
                    from_=self._whatsapp_from,
                    content_sid=actual_template_id,
                    content_variables=json.dumps(template_variables),
                )
            else:
                # Fallback: construct approved template text
                # Template: 🎬 TicketRadar Alert!\n\nBooking is now open for *{1}* on *{2}*.\n\nBook now: {3}\n\n_Reply STOP to opt out._
                movie_name = template_variables.get("1", template_variables.get("movie_name", "Movie"))
                date_str = template_variables.get("2", template_variables.get("date_str", ""))
                url = template_variables.get("3", template_variables.get("url", ""))
                body = (
                    f"🎬 *TicketRadar Alert!*\n\n"
                    f"Booking is now open for *{movie_name}* on *{date_str}*.\n\n"
                    f"Book now: {url}\n\n"
                    f"_Reply STOP to opt out._"
                )
                return client.messages.create(
                    to=target,
                    from_=self._whatsapp_from,
                    body=body,
                )

        try:
            msg = await asyncio.to_thread(_call_twilio)
            logger.info(f"Twilio WhatsApp dispatched. SID: {msg.sid}, to: {redact_phone(to)}")
            return ProviderMessageResult(
                success=True,
                provider_id=msg.sid,
            )
        except TwilioRestException as tre:
            logger.error(f"Twilio WhatsApp Rest error: code={tre.code}, msg={tre.msg}, to={redact_phone(to)}")
            return ProviderMessageResult(
                success=False,
                provider_id="",
                error_code=str(tre.code),
                error_message=str(tre.msg),
            )
        except Exception as e:
            logger.error(f"Twilio WhatsApp general error: {e}, to={redact_phone(to)}")
            return ProviderMessageResult(
                success=False,
                provider_id="",
                error_code="TWILIO_WHATSAPP_ERROR",
                error_message=str(e),
            )

    async def initiate_call(
        self,
        to: str,
        twiml_or_answer_url: str,
        status_callback_url: str,
        idempotency_key: str,
    ) -> ProviderCallResult:
        """Initiate outbound phone call via Twilio Voice API."""
        def _call_twilio():
            client = self._get_client()
            return client.calls.create(
                to=to,
                from_=self._from_number,
                url=twiml_or_answer_url,
                status_callback=status_callback_url,
                status_callback_event=["initiated", "ringing", "answered", "completed"],
                status_callback_method="POST",
            )

        try:
            call = await asyncio.to_thread(_call_twilio)
            logger.info(f"Twilio Call initiated. SID: {call.sid}, to: {redact_phone(to)}")
            return ProviderCallResult(
                success=True,
                call_id=call.sid,
            )
        except TwilioRestException as tre:
            logger.error(f"Twilio Voice Rest error: code={tre.code}, msg={tre.msg}, to={redact_phone(to)}")
            return ProviderCallResult(
                success=False,
                call_id="",
                error_code=str(tre.code),
                error_message=str(tre.msg),
            )
        except Exception as e:
            logger.error(f"Twilio Voice general error: {e}, to={redact_phone(to)}")
            return ProviderCallResult(
                success=False,
                call_id="",
                error_code="TWILIO_CALL_ERROR",
                error_message=str(e),
            )

    def validate_incoming_webhook(
        self,
        raw_body: bytes,
        headers: Dict[str, str],
        url: str,
    ) -> bool:
        """
        Validate incoming Twilio webhook using X-Twilio-Signature.
        """
        if not self._validator:
            # If Twilio auth token not set, cannot validate
            return False

        signature = headers.get("X-Twilio-Signature") or headers.get("x-twilio-signature", "")
        if not signature:
            return False

        # Parse form parameters from body
        params = {}
        if raw_body:
            try:
                parsed_qs = urllib.parse.parse_qs(raw_body.decode("utf-8", errors="replace"), keep_blank_values=True)
                # parse_qs returns dict of lists; Twilio validator expects flat dict of strings
                params = {k: v[0] if len(v) == 1 else v for k, v in parsed_qs.items()}
            except Exception:
                params = {}

        return self._validator.validate(url, params, signature)

    def parse_message_status_event(self, form_data: Dict[str, Any]) -> Dict[str, Any]:
        """Parse status callback payload for SMS and WhatsApp."""
        status = str(form_data.get("MessageStatus") or form_data.get("SmsStatus") or "").lower()
        return {
            "provider_id": form_data.get("MessageSid") or form_data.get("SmsSid") or "",
            "status": status,
            "error_code": form_data.get("ErrorCode"),
            "error_message": form_data.get("ErrorMessage"),
            "to": form_data.get("To", ""),
            "from": form_data.get("From", ""),
        }

    def parse_call_status_event(self, form_data: Dict[str, Any]) -> Dict[str, Any]:
        """Parse status callback payload for Voice calls."""
        call_status = str(form_data.get("CallStatus") or "").lower()
        duration = form_data.get("CallDuration")
        try:
            duration_sec = int(duration) if duration is not None else 0
        except (ValueError, TypeError):
            duration_sec = 0

        # Outcome classification:
        # answered: completed with duration > 0 or in-progress
        # no_answer: no-answer
        # busy: busy
        # failed: failed
        if call_status == "completed" and duration_sec > 0:
            outcome = "answered"
        elif call_status == "completed" and duration_sec == 0:
            outcome = "no_answer"
        elif call_status in ("in-progress", "answered"):
            outcome = "answered"
        elif call_status in ("no-answer", "ringing"):
            outcome = "no_answer"
        elif call_status == "busy":
            outcome = "busy"
        else:
            outcome = "failed"

        return {
            "provider_id": form_data.get("CallSid", ""),
            "status": call_status,
            "duration": duration_sec,
            "answered": outcome == "answered",
            "call_outcome": outcome,
            "error_code": form_data.get("ErrorCode"),
        }
