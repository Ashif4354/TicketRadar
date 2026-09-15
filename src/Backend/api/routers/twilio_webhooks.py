# src/Backend/api/routers/twilio_webhooks.py

import logging
from fastapi import APIRouter, Request, HTTPException, Response
from google.cloud import firestore

from lib.core.auth import db
from lib.core.monitor import JobManager
from lib.providers.notification.factory import NotificationProviderFactory
from lib.services.wallet import WalletService
from lib.services.notification.factory import NotificationStrategyFactory
from lib.utils.redact import redact_phone

logger = logging.getLogger("ticketradar.api.twilio_webhooks")
manager = JobManager()

router = APIRouter(prefix="/api/twilio", tags=["Twilio Webhooks"])

@router.post("/voice-twiml/{job_id}")
async def get_voice_twiml(job_id: str):
    """
    Returns TwiML instructions for Twilio Voice calls using Amazon Polly TTS (en-IN).
    """
    movie_name = "your monitored movie"
    date_str = ""

    job = manager.get_job(job_id)
    if job:
        movie_name = job.movie_name or movie_name
        date_str = job.date_str or ""
    elif db:
        try:
            doc = db.collection("notification_jobs").document(job_id).get()
            if not doc.exists:
                doc = db.collection("jobs").document(job_id).get()
            if doc.exists:
                data = doc.to_dict() or {}
                movie_name = data.get("movie_name") or movie_name
                date_str = data.get("params", {}).get("date_str") or ""
        except Exception as e:
            logger.warning(f"Failed to fetch job for TwiML: {e}")

    date_formatted = f"for show date {date_str}" if date_str else ""
    twiml = (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<Response>\n'
        '    <Pause length="1"/>\n'
        '    <Say voice="Polly.Aditi" language="en-IN">\n'
        f'        Hello from TicketRadar! Booking is now open for {movie_name} {date_formatted}. '
        'Please check your BookMyShow app to book your seats right now. Thank you!\n'
        '    </Say>\n'
        '    <Pause length="1"/>\n'
        '</Response>'
    )
    logger.info(f"Generated TwiML voice response for job {job_id} ({movie_name})")
    return Response(content=twiml, media_type="application/xml")

@router.post("/call-status")
async def handle_call_status(request: Request):
    """
    Status callback for Twilio Voice calls.
    Validates Twilio signature and advances notification state machine.
    """
    from datetime import datetime, timezone
    raw_body = await request.body()
    headers = dict(request.headers)
    adapter = NotificationProviderFactory.create()

    # Signature verification (in production)
    url = str(request.url)
    if not adapter.validate_incoming_webhook(raw_body, headers, url):
        import os
        from lib.utils.config import settings
        disable_sec = os.getenv("DISABLE_SECURITY", "").lower() in ("true", "1") or (settings and getattr(settings, "disable_security", False))
        if not disable_sec:
            logger.warning("Twilio call-status signature validation failed.")
            raise HTTPException(status_code=403, detail="Invalid Twilio signature.")

    form_data = await request.form()
    event = adapter.parse_call_status_event(dict(form_data))
    call_sid = event.get("provider_id", "")
    status = event.get("status", "")
    call_outcome = event.get("call_outcome", "")

    if not call_sid:
        return {"status": "ignored", "reason": "no call_sid"}

    event_id = f"twilio_call_{call_sid}_{status}"

    # Extract job_id from query params or twilio_calls
    job_id = request.query_params.get("job_id", "")
    call_record = {}
    if db:
        call_doc = db.collection("twilio_calls").document(call_sid).get()
        if call_doc.exists:
            call_record = call_doc.to_dict() or {}
            if not job_id:
                job_id = call_record.get("job_id", "")

    if db:
        event_ref = db.collection("webhook_events").document(event_id)
        if event_ref.get().exists:
            return {"status": "duplicate", "event_id": event_id}

        event_ref.set({
            "id": event_id,
            "source": "twilio_call",
            "event_type": status,
            "raw_payload": dict(form_data),
            "signature_valid": True,
            "processed": True,
            "received_at": firestore.SERVER_TIMESTAMP,
        })

        # Save call record
        db.collection("twilio_calls").document(call_sid).set({
            "call_sid": call_sid,
            "job_id": job_id,
            "status": status,
            "duration_seconds": event.get("duration", 0),
            "answered": event.get("answered", False),
            "call_outcome": call_outcome,
            "updated_at": firestore.SERVER_TIMESTAMP,
        }, merge=True)

    logger.info(f"Twilio call status callback: {call_sid} -> {status} (outcome: {call_outcome}, job: {job_id})")

    # Advance notification state machine for this job
    if job_id:
        job = manager.get_job(job_id)
        if not job and db:
            j_doc = db.collection("notification_jobs").document(job_id).get()
            if j_doc.exists:
                from lib.core.job import MonitorJob
                job = MonitorJob.from_dict(j_doc.to_dict())
                manager.jobs[job.id] = job

        if job:
            if call_outcome == "answered":
                job.notification_status = "delivered"
                job.notification_sent = True
                job.notification_delivered_at = datetime.now(timezone.utc)
                manager._save_job_to_firestore(job)
                if db:
                    db.collection("notification_job_channels").document(job.id).set({
                        "last_attempt_outcome": "answered",
                        "last_attempt_at": firestore.SERVER_TIMESTAMP,
                    }, merge=True)

                # Send dedicated Call Success email
                user_email = job.creator_email
                user_name = "User"
                if db and job.created_by:
                    try:
                        udoc = db.collection("users").document(job.created_by).get()
                        if udoc.exists:
                            udata = udoc.to_dict() or {}
                            user_email = udata.get("email") or user_email
                            user_name = udata.get("displayName") or user_name
                    except Exception:
                        pass
                if user_email:
                    from lib.services.notification.user_mailer import send_call_success_email
                    import asyncio
                    try:
                        asyncio.create_task(send_call_success_email(
                            recipient_email=user_email,
                            user_name=user_name,
                            phone_number=job.phone_number or call_record.get("to_number_redacted", ""),
                            movie_name=job.movie_name,
                            date_str=job.date_str,
                            call_duration_seconds=event.get("duration", 0),
                            url=job.url
                        ))
                    except Exception as cse_err:
                        logger.debug(f"Failed to dispatch call success email: {cse_err}")

            elif call_outcome in ("no_answer", "busy"):
                attempt = job.notification_attempt_count or 1
                if attempt < 3:
                    # Retry
                    job.notification_attempt_count = attempt + 1
                    try:
                        notifier = NotificationStrategyFactory.create_strategy(
                            job.notification_medium,
                            job.notification_config,
                            job_id=job.id
                        )
                        await notifier.send_notification(
                            subject=f"TicketRadar: Booking Open for {job.date_str}!",
                            movie_name=job.movie_name,
                            date_str=job.date_str,
                            available_theatres=job.theatres,
                            unavailable_theatres=[],
                            url=job.url,
                            language=job.language,
                            format_name=job.format_name
                        )
                    except Exception as re_err:
                        logger.warning(f"Retry call failed for {job.id}: {re_err}")
                else:
                    # Policy exempt delivery: 3x unanswered/busy -> no refund, fallback email
                    job.notification_status = "policy_exempt"
                    job.notification_sent = True
                    manager._save_job_to_firestore(job)
                    if db:
                        db.collection("notification_job_channels").document(job.id).set({
                            "last_attempt_outcome": "policy_exempt",
                            "last_attempt_at": firestore.SERVER_TIMESTAMP,
                        }, merge=True)

                    # Send fallback email with dedicated 3x call unanswered template
                    fallback_enabled = True
                    fallback_email = job.creator_email
                    user_name = "User"
                    if db and job.created_by:
                        try:
                            pdoc = db.collection("notification_preferences").document(job.created_by).get()
                            if pdoc.exists:
                                pdata = pdoc.to_dict() or {}
                                fallback_enabled = pdata.get("email_fallback_on_no_answer", True)
                                if pdata.get("email_address"):
                                    fallback_email = pdata.get("email_address")
                            udoc = db.collection("users").document(job.created_by).get()
                            if udoc.exists:
                                user_name = (udoc.to_dict() or {}).get("displayName") or user_name
                        except Exception:
                            pass

                    if fallback_enabled and fallback_email:
                        from lib.services.notification.user_mailer import send_call_unanswered_email
                        import asyncio
                        try:
                            asyncio.create_task(send_call_unanswered_email(
                                recipient_email=fallback_email,
                                user_name=user_name,
                                phone_number=job.phone_number or call_record.get("to_number_redacted", ""),
                                movie_name=job.movie_name,
                                date_str=job.date_str,
                                available_theatres=job.theatres,
                                url=job.url,
                                attempt_count=3
                            ))
                            if db:
                                db.collection("notification_job_channels").document(job.id).set({
                                    "fallback_email_sent": True
                                }, merge=True)
                        except Exception as fe_err:
                            logger.error(f"Fallback email send error for {job.id}: {fe_err}")

            elif call_outcome == "failed":
                attempt = job.notification_attempt_count or 1
                if attempt < 3:
                    job.notification_attempt_count = attempt + 1
                    try:
                        notifier = NotificationStrategyFactory.create_strategy(
                            job.notification_medium,
                            job.notification_config,
                            job_id=job.id
                        )
                        await notifier.send_notification(
                            subject=f"TicketRadar: Booking Open for {job.date_str}!",
                            movie_name=job.movie_name,
                            date_str=job.date_str,
                            available_theatres=job.theatres,
                            unavailable_theatres=[],
                            url=job.url,
                            language=job.language,
                            format_name=job.format_name
                        )
                    except Exception:
                        pass
                else:
                    job.notification_status = "failed"
                    manager._save_job_to_firestore(job)
                    if job.price_paise > 0 and not job.refund_issued and job.created_by:
                        try:
                            WalletService.credit(
                                uid=job.created_by,
                                amount_paise=job.price_paise,
                                txn_type="JOB_REFUND",
                                description=f"Refund for job #{job.id}: phone call failed",
                                idempotency_key=f"notif_fail_refund_{job.id}",
                                job_id=job.id,
                            )
                            job.refund_issued = True
                        except Exception as rerr:
                            logger.error(f"Call refund failed for {job.id}: {rerr}")

    return {"status": "processed", "call_sid": call_sid}

@router.post("/message-status")
async def handle_message_status(request: Request):
    """
    Status callback for Twilio SMS and WhatsApp messages.
    Validates Twilio signature and updates message and job delivery status.
    """
    from datetime import datetime, timezone
    raw_body = await request.body()
    headers = dict(request.headers)
    adapter = NotificationProviderFactory.create()

    url = str(request.url)
    if not adapter.validate_incoming_webhook(raw_body, headers, url):
        import os
        from lib.utils.config import settings
        disable_sec = os.getenv("DISABLE_SECURITY", "").lower() in ("true", "1") or (settings and getattr(settings, "disable_security", False))
        if not disable_sec:
            logger.warning("Twilio message-status signature validation failed.")
            raise HTTPException(status_code=403, detail="Invalid Twilio signature.")

    form_data = await request.form()
    event = adapter.parse_message_status_event(dict(form_data))
    message_sid = event.get("provider_id", "")
    status = event.get("status", "")

    if not message_sid:
        return {"status": "ignored", "reason": "no message_sid"}

    event_id = f"twilio_msg_{message_sid}_{status}"

    job_id = request.query_params.get("job_id", "")
    if db:
        msg_doc = db.collection("twilio_messages").document(message_sid).get()
        if msg_doc.exists and not job_id:
            job_id = (msg_doc.to_dict() or {}).get("job_id", "")

    if db:
        event_ref = db.collection("webhook_events").document(event_id)
        if event_ref.get().exists:
            return {"status": "duplicate", "event_id": event_id}

        event_ref.set({
            "id": event_id,
            "source": "twilio_message",
            "event_type": status,
            "raw_payload": dict(form_data),
            "signature_valid": True,
            "processed": True,
            "received_at": firestore.SERVER_TIMESTAMP,
        })

        db.collection("twilio_messages").document(message_sid).set({
            "message_sid": message_sid,
            "job_id": job_id,
            "status": status,
            "error_code": event.get("error_code"),
            "error_message": event.get("error_message"),
            "updated_at": firestore.SERVER_TIMESTAMP,
        }, merge=True)

    logger.info(f"Twilio message status callback: {message_sid} -> {status} (job: {job_id})")

    if job_id:
        job = manager.get_job(job_id)
        if not job and db:
            j_doc = db.collection("notification_jobs").document(job_id).get()
            if j_doc.exists:
                from lib.core.job import MonitorJob
                job = MonitorJob.from_dict(j_doc.to_dict())
                manager.jobs[job.id] = job

        if job:
            if status in ("delivered", "read"):
                job.notification_status = "delivered"
                job.notification_sent = True
                job.notification_delivered_at = datetime.now(timezone.utc)
                manager._save_job_to_firestore(job)
                if db:
                    db.collection("notification_job_channels").document(job.id).set({
                        "last_attempt_outcome": status,
                        "last_attempt_at": firestore.SERVER_TIMESTAMP,
                    }, merge=True)

            elif status in ("undelivered", "failed"):
                attempt = job.notification_attempt_count or 1
                if attempt < 3:
                    job.notification_attempt_count = attempt + 1
                    try:
                        notifier = NotificationStrategyFactory.create_strategy(
                            job.notification_medium,
                            job.notification_config,
                            job_id=job.id
                        )
                        await notifier.send_notification(
                            subject=f"TicketRadar: Booking Open for {job.date_str}!",
                            movie_name=job.movie_name,
                            date_str=job.date_str,
                            available_theatres=job.theatres,
                            unavailable_theatres=[],
                            url=job.url,
                            language=job.language,
                            format_name=job.format_name
                        )
                    except Exception:
                        pass
                else:
                    job.notification_status = "failed"
                    manager._save_job_to_firestore(job)
                    if job.price_paise > 0 and not job.refund_issued and job.created_by:
                        try:
                            WalletService.credit(
                                uid=job.created_by,
                                amount_paise=job.price_paise,
                                txn_type="JOB_REFUND",
                                description=f"Refund for job #{job.id}: {job.notification_medium} delivery failed",
                                idempotency_key=f"notif_fail_refund_{job.id}",
                                job_id=job.id,
                            )
                            job.refund_issued = True
                        except Exception as rerr:
                            logger.error(f"Message refund failed for {job.id}: {rerr}")

    return {"status": "processed", "message_sid": message_sid}

@router.post("/whatsapp-incoming")
async def handle_whatsapp_incoming(request: Request):
    """
    Webhook for incoming WhatsApp messages (e.g. STOP to opt-out).
    """
    form_data = await request.form()
    body = (form_data.get("Body") or "").strip().upper()
    from_number = form_data.get("From") or ""
    phone = from_number.replace("whatsapp:", "").strip()

    if body == "STOP" and phone and db:
        from lib.utils.phone import normalize_indian_phone
        try:
            phone_norm = normalize_indian_phone(phone)
        except Exception:
            phone_norm = phone

        # Revoke WhatsApp consent for any users with this phone
        logger.info(f"WhatsApp STOP received from {redact_phone(phone)}. Revoking consent.")
        for p in set([phone, phone_norm]):
            docs = db.collection("notification_consents").where("phone_number", "==", p).stream()
            for doc in docs:
                db.collection("notification_consents").document(doc.id).set({
                    "whatsapp_consented": False,
                    "whatsapp_revoked_at": firestore.SERVER_TIMESTAMP,
                }, merge=True)

    twiml = '<?xml version="1.0" encoding="UTF-8"?><Response></Response>'
    return Response(content=twiml, media_type="application/xml")
