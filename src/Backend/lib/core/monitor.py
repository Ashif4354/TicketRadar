# src/core/monitor.py

import asyncio
import threading
import time
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime, timezone
from google.cloud import firestore

from .job import MonitorJob
from ..utils.logger import get_job_logger
from ..services.scraper.factory import ScraperFactory
from ..services.notification.factory import NotificationStrategyFactory
from ..services.gcp_logger import gcp_logger, current_job_id, current_job_creator
from ..services.wallet import WalletService

logger = logging.getLogger(__name__)

class JobManager:
    """
    Singleton Manager (Singleton Pattern) that controls the lifecycle
    of background ticket booking monitor tasks as asynchronous tasks
    running on a dedicated background event loop.
    """
    _instance = None
    _lock = threading.Lock()

    def __new__(cls, *args, **kwargs):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(JobManager, cls).__new__(cls)
                cls._instance._initialized = False
            return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._initialized = True
        self.jobs: Dict[str, MonitorJob] = {}
        self.stop_events: Dict[str, asyncio.Event] = {}
        self.lock = threading.Lock()
        
        # Initialize background event loop for async tasks
        self.loop = asyncio.new_event_loop()
        self.loop_thread = threading.Thread(
            target=self._run_async_loop,
            args=(self.loop,),
            name="BMS-AsyncLoop",
            daemon=True
        )
        self.loop_thread.start()
        logger.info("JobManager Singleton initialized. Async background loop running.")
        
        # Hydrate active jobs from Firestore and auto-resume running tasks
        self._load_jobs_from_firestore()
        self._resume_running_jobs()

    def _run_async_loop(self, loop: asyncio.AbstractEventLoop) -> None:
        """Runs the asyncio event loop forever in a background thread."""
        asyncio.set_event_loop(loop)
        loop.run_forever()

    async def _create_event(self) -> asyncio.Event:
        """Helper coroutine to create an Event on the loop thread."""
        return asyncio.Event()

    def _save_job_to_firestore(self, job: MonitorJob) -> None:
        """Upserts a MonitorJob document into Firestore ('notification_jobs' and 'jobs')."""
        try:
            from .auth import db
            if db:
                data = job.to_dict()
                db.collection("notification_jobs").document(job.id).set(data, merge=True)
                db.collection("jobs").document(job.id).set(data, merge=True)
                logger.debug(f"Saved job {job.id} to Firestore.")
        except Exception as e:
            logger.error(f"Failed to save job {job.id} to Firestore: {e}")

    def _delete_job_from_firestore(self, job_id: str) -> None:
        """Deletes a job document from Firestore ('notification_jobs' and 'jobs')."""
        try:
            from .auth import db
            if db:
                db.collection("notification_jobs").document(job_id).delete()
                db.collection("jobs").document(job_id).delete()
                logger.info(f"Deleted job {job_id} from Firestore.")
        except Exception as e:
            logger.error(f"Failed to delete job {job_id} from Firestore: {e}")

    def _load_jobs_from_firestore(self) -> None:
        """Loads active/non-deleted jobs from Firestore upon startup."""
        try:
            from .auth import db
            if not db:
                logger.warning("Firestore client not available. Skipping job restoration from Firestore.")
                return

            docs = list(db.collection("notification_jobs").stream())
            if not docs:
                docs = list(db.collection("jobs").stream())

            loaded_count = 0
            with self.lock:
                for doc in docs:
                    data = doc.to_dict()
                    if not data:
                        continue
                    if data.get("status") == "Deleted":
                        continue
                    job = MonitorJob.from_dict(data)
                    self.jobs[job.id] = job
                    loaded_count += 1

            logger.info(f"Successfully restored {loaded_count} active job(s) from Firestore.")
        except Exception as e:
            logger.error(f"Failed to load jobs from Firestore: {e}")

    def _resume_running_jobs(self) -> None:
        """Automatically restarts monitoring loops for jobs that were in 'Running' state."""
        with self.lock:
            running_jobs = [job for job in list(self.jobs.values()) if job.status == "Running"]
        
        if not running_jobs:
            return

        logger.info(f"Found {len(running_jobs)} active running job(s) to resume on startup.")
        for job in running_jobs:
            # Temporarily reset status so start_job doesn't reject it as already running
            job.status = "Idle"
            success = self.start_job(job)
            if success:
                logger.info(f"⚡ Auto-resumed monitor loop for job #{job.id} ({job.movie_name}).")
            else:
                logger.warning(f"Failed to auto-resume job #{job.id}.")

    def stop_all_jobs_for_shutdown(self) -> None:
        """Stops background monitoring loops for all jobs on server shutdown without altering persistent job status."""
        logger.info("Signaling background monitor tasks to stop for server shutdown...")
        with self.lock:
            for job_id, event in list(self.stop_events.items()):
                try:
                    self.loop.call_soon_threadsafe(event.set)
                except Exception as e:
                    logger.error(f"Error setting stop event for job {job_id} on shutdown: {e}")

    def start_job(self, job: MonitorJob) -> bool:
        """Starts a background async monitor task for the given job."""
        with self.lock:
            if job.id in self.jobs and self.jobs[job.id].status == "Running":
                logger.warning(f"Job {job.id} is already running.")
                return False

            self.jobs[job.id] = job
            
            # Create an asyncio.Event inside the loop's thread context
            try:
                future = asyncio.run_coroutine_threadsafe(self._create_event(), self.loop)
                stop_event = future.result(timeout=2.0)  # Wait for creation
            except Exception as e:
                logger.error(f"Failed to create stop event for job {job.id}: {e}")
                return False
                
            self.stop_events[job.id] = stop_event
            
            # Schedule the monitoring loop coroutine on the background event loop
            asyncio.run_coroutine_threadsafe(
                self._run_job_loop(job, stop_event),
                self.loop
            )
            
            job.update_state("Running", "Starting monitoring loop...")
            self._save_job_to_firestore(job)
            logger.info(f"Asynchronous task scheduled on loop for job {job.id}.")
            return True

    def stop_job(self, job_id: str) -> bool:
        """Signals a background async job to stop."""
        with self.lock:
            if job_id not in self.jobs:
                return False
            
            job = self.jobs[job_id]
            if job_id in self.stop_events:
                # Safely trigger event set inside the event loop thread
                event = self.stop_events[job_id]
                self.loop.call_soon_threadsafe(event.set)
                logger.info(f"Stop signal sent (Event set) for job {job_id}.")
            
            job.update_state("Stopped", "Monitoring stopped by user.")
            self._save_job_to_firestore(job)
            return True

    def claim_cancellation(self, job_id: str) -> dict:
        """
        Transactional claim for job cancellation to prevent race with notification dispatch.
        Returns:
            {"ok": False, "reason": "notification_in_progress"}
            {"ok": True, "refund": False}  # already delivered
            {"ok": True, "refund": True}   # eligible for refund
        """
        from .auth import db
        job = self.get_job(job_id)
        if job and job.notification_status == "dispatched":
            return {"ok": False, "reason": "notification_in_progress"}
        if job and job.notification_sent:
            return {"ok": True, "refund": False}

        if db:
            job_ref = db.collection("notification_jobs").document(job_id)
            try:
                @firestore.transactional
                def _txn_cancel(transaction):
                    snap = job_ref.get(transaction=transaction)
                    if not snap.exists:
                        if job and job.notification_sent:
                            return {"ok": True, "refund": False}
                        return {"ok": True, "refund": True}
                    data = snap.to_dict() or {}
                    if data.get("notification_status") == "dispatched":
                        return {"ok": False, "reason": "notification_in_progress"}
                    if data.get("notification_sent"):
                        return {"ok": True, "refund": False}
                    transaction.update(job_ref, {
                        "status": "cancelling",
                        "updated_at": firestore.SERVER_TIMESTAMP,
                    })
                    return {"ok": True, "refund": True}

                return _txn_cancel(db.transaction())
            except Exception as e:
                logger.error(f"Error in claim_cancellation transaction for {job_id}: {e}")
                if job:
                    if job.notification_status == "dispatched":
                        return {"ok": False, "reason": "notification_in_progress"}
                    if job.notification_sent:
                        return {"ok": True, "refund": False}
                return {"ok": True, "refund": True}

        return {"ok": True, "refund": not (job and job.notification_sent)}

    def claim_notification_slot(self, job: MonitorJob) -> bool:
        """
        Transactional claim before dispatching notification.
        Prevents race condition with job cancellation.
        """
        from .auth import db
        with job._lock:
            if job.status in ("Stopped", "Cancelling"):
                return False
            if job.notification_sent:
                return False
            if job.notification_status == "dispatched":
                return False

        if db:
            job_ref = db.collection("notification_jobs").document(job.id)
            try:
                @firestore.transactional
                def _txn_claim(transaction):
                    snap = job_ref.get(transaction=transaction)
                    if not snap.exists:
                        return True
                    data = snap.to_dict() or {}
                    st = str(data.get("status", "")).lower()
                    if st in ("stopped", "cancelling", "deleted"):
                        return False
                    if data.get("notification_sent"):
                        return False
                    if data.get("notification_status") == "dispatched":
                        return False
                    transaction.update(job_ref, {
                        "notification_status": "dispatched",
                        "notification_dispatched_at": firestore.SERVER_TIMESTAMP,
                    })
                    return True

                claimed = _txn_claim(db.transaction())
                if not claimed:
                    return False
            except Exception as e:
                logger.error(f"Error in claim_notification_slot transaction for {job.id}: {e}")

        with job._lock:
            job.notification_status = "dispatched"
            job.notification_dispatched_at = datetime.now(timezone.utc)
        self._save_job_to_firestore(job)
        return True

    def delete_job(self, job_id: str, refund_eligible: Optional[bool] = None) -> bool:
        """Stops and deletes a job, processing cancellation refunds if eligible."""
        job = self.get_job(job_id)
        if job:
            if refund_eligible is None:
                claim_res = self.claim_cancellation(job_id)
                if not claim_res.get("ok"):
                    logger.warning(f"Cannot delete job {job_id}: {claim_res.get('reason')}")
                    return False
                refund_eligible = claim_res.get("refund", False)

            # If not delivered, not already refunded, price > 0, and refund_eligible -> refund to wallet
            if refund_eligible and job.price_paise > 0 and not job.notification_sent and not job.refund_issued and job.created_by:
                try:
                    WalletService.credit(
                        uid=job.created_by,
                        amount_paise=job.price_paise,
                        txn_type="JOB_REFUND",
                        description=f"Refund for job #{job.id}: job cancelled before notification",
                        idempotency_key=f"cancel_refund_{job.id}",
                        job_id=job.id,
                    )
                    job.refund_issued = True
                    logger.info(f"Cancellation refund issued for job {job.id}.")
                except Exception as re:
                    logger.error(f"Failed to issue cancel refund for {job.id}: {re}")

        self.stop_job(job_id)
        
        # Give a small window for the loop to register the event and exit
        time.sleep(0.5)
        
        with self.lock:
            if job_id in self.jobs:
                del self.jobs[job_id]
            if job_id in self.stop_events:
                del self.stop_events[job_id]
                
        self._delete_job_from_firestore(job_id)
        # Log job deletion
        logger.info(f"Job {job_id} completely deleted and cleaned.")
        return True


    def get_job(self, job_id: str) -> Optional[MonitorJob]:
        """Retrieves a job by its ID."""
        with self.lock:
            return self.jobs.get(job_id)

    def get_all_jobs(self) -> List[MonitorJob]:
        """Returns a list of all jobs."""
        with self.lock:
            return list(self.jobs.values())

    async def _run_job_loop(self, job: MonitorJob, stop_event: asyncio.Event) -> None:
        """
        Run the monitoring cycle until it is stopped or a booking is found.
        
        Parameters:
            job (MonitorJob): Job configuration and state to monitor.
            stop_event (asyncio.Event): Event that signals the monitoring cycle to stop.
        """
        job_logger = get_job_logger(job.id)
        job_logger.info(
            f"🚀  Monitor started — watching \"{job.movie_name}\" "
            f"for {job.date_str} every {job.check_interval}s."
        )

        scraper = ScraperFactory.create_scraper(job.service_provider)
        creator_email = job.creator_email or job.created_by or "system"
        tok_id = current_job_id.set(job.id)
        tok_creator = current_job_creator.set(creator_email)

        try:
            while not stop_event.is_set():
                job_logger.info("🔄  Checking availability on BookMyShow...")

                # Perform scraping check asynchronously
                try:
                    success, details, movie_name, available, unavailable = await scraper.check_booking(
                        job.params,
                        logger=job_logger
                    )
                    if movie_name and movie_name != "Fetching...":
                        if job.movie_name != movie_name:
                            job_logger.info(f"Movie name updated from page: '{job.movie_name}' -> '{movie_name}'")
                            job.movie_name = movie_name
                            self._save_job_to_firestore(job)
                except Exception as e:
                    success = False
                    details = "An unexpected error occurred during the check."
                    available, unavailable = [], job.theatres
                    job_logger.error(f"⚠️  Something went wrong during the check. Will retry. ({e})")

                if stop_event.is_set():
                    break

                if success:
                    # 1. Concurrency protection & deduplication claim
                    if not self.claim_notification_slot(job):
                        job_logger.info("Notification slot could not be claimed (job cancelled or already sent). Skipping dispatch.")
                        break

                    # 2. Consent verification for regulated channels
                    medium_norm = job.notification_medium.lower().replace(" ", "_")
                    consent_ok = True
                    if medium_norm in ("whatsapp", "sms", "phone_call", "call") and job.created_by:
                        try:
                            from .auth import db
                            if db:
                                cdoc = db.collection("notification_consents").document(job.created_by).get()
                                if cdoc.exists:
                                    cdata = cdoc.to_dict() or {}
                                    if "whatsapp" in medium_norm and cdata.get("whatsapp_consented") is False:
                                        consent_ok = False
                                    elif "sms" in medium_norm and cdata.get("sms_consented") is False:
                                        consent_ok = False
                                    elif ("call" in medium_norm or "phone" in medium_norm) and (cdata.get("call_consented") is False and cdata.get("phone_call_consented") is False):
                                        consent_ok = False
                        except Exception as ce:
                            job_logger.warning(f"Error checking user consent: {ce}")

                    if not consent_ok:
                        job_logger.warning("Consent revoked by user before notification dispatch. Aborting delivery.")
                        job.update_state("Error", "Notification aborted: user consent revoked.")
                        job.notification_status = "failed"
                        if job.price_paise > 0 and not job.refund_issued and job.created_by:
                            try:
                                WalletService.credit(
                                    uid=job.created_by,
                                    amount_paise=job.price_paise,
                                    txn_type="JOB_REFUND",
                                    description=f"Refund for job #{job.id}: consent revoked",
                                    idempotency_key=f"consent_revoke_refund_{job.id}",
                                    job_id=job.id,
                                )
                                job.refund_issued = True
                            except Exception as re:
                                job_logger.error(f"Failed to issue consent revoke refund: {re}")
                        self._save_job_to_firestore(job)
                        break

                    # 3. Retries: up to 3 attempts without delay on failures
                    max_attempts = 3
                    notif_success = False
                    notif_msg = ""
                    notifier = None

                    try:
                        notif_cfg = dict(job.notification_config)
                        if job.phone_number and "phone_number" not in notif_cfg:
                            notif_cfg["phone_number"] = job.phone_number

                        notifier = NotificationStrategyFactory.create_strategy(
                            job.notification_medium,
                            notif_cfg,
                            job_id=job.id
                        )
                    except Exception as ne:
                        job_logger.error(f"Failed to create notification strategy: {ne}")
                        notif_msg = str(ne)

                    if notifier:
                        import re
                        from ..utils.redact import redact_phone
                        subject = f"TicketRadar: Booking Open for {job.date_str}!"
                        for attempt in range(1, max_attempts + 1):
                            job.notification_attempt_count = attempt
                            try:
                                notif_success, notif_msg = await notifier.send_notification(
                                    subject=subject,
                                    movie_name=job.movie_name,
                                    date_str=job.date_str,
                                    available_theatres=available,
                                    unavailable_theatres=unavailable,
                                    url=job.url,
                                    language=job.language,
                                    format_name=job.format_name
                                )
                            except Exception as notif_err:
                                notif_success = False
                                notif_msg = str(notif_err)

                            # Extract provider SID if available
                            provider_sid = None
                            sid_match = re.search(r'(?:SID|Call SID):\s*([A-Za-z0-9_]+)', notif_msg)
                            if sid_match:
                                provider_sid = sid_match.group(1)

                            # Record attempt in channel state
                            try:
                                from .auth import db
                                if db:
                                    ch_data = {
                                        "job_id": job.id,
                                        "uid": job.created_by,
                                        "medium": job.notification_medium,
                                        "attempt_count": attempt,
                                        "last_attempt_at": firestore.SERVER_TIMESTAMP,
                                        "last_attempt_outcome": notif_msg,
                                    }
                                    if provider_sid:
                                        ch_data["current_attempt_provider_id"] = provider_sid
                                    db.collection("notification_job_channels").document(job.id).set(ch_data, merge=True)

                                    # Create tracking doc for provider callbacks
                                    if provider_sid:
                                        if "call" in medium_norm or "phone" in medium_norm:
                                            db.collection("twilio_calls").document(provider_sid).set({
                                                "call_sid": provider_sid,
                                                "job_id": job.id,
                                                "uid": job.created_by,
                                                "to_number_redacted": redact_phone(job.phone_number),
                                                "status": "initiated",
                                                "call_outcome": "initiated",
                                                "attempt_number": attempt,
                                                "created_at": firestore.SERVER_TIMESTAMP,
                                            }, merge=True)
                                        else:
                                            db.collection("twilio_messages").document(provider_sid).set({
                                                "message_sid": provider_sid,
                                                "job_id": job.id,
                                                "uid": job.created_by,
                                                "medium": "sms" if "sms" in medium_norm else "whatsapp",
                                                "to_number_redacted": redact_phone(job.phone_number),
                                                "status": "sent",
                                                "attempt_number": attempt,
                                                "created_at": firestore.SERVER_TIMESTAMP,
                                            }, merge=True)
                            except Exception:
                                pass

                            if notif_success:
                                break
                            else:
                                job_logger.warning(f"Notification attempt {attempt}/{max_attempts} failed: {notif_msg}")

                    # 4. Handle notification dispatch outcome
                    if notif_success:
                        job_logger.info(
                            f"📣 Alert dispatched via {job.notification_medium.upper()}!"
                        )
                        if medium_norm in ("email", "discord", "discord_webhook"):
                            job.notification_sent = True
                            job.notification_status = "delivered"
                            job.notification_delivered_at = datetime.now(timezone.utc)
                        else:
                            job.notification_status = "dispatched"
                            job.notification_dispatched_at = datetime.now(timezone.utc)

                        status_msg = f"{details} Alert sent."
                        if unavailable:
                            status_msg += " Tracking paused — resume from dashboard to monitor remaining unavailable theatres."
                        job.update_state("Success", status_msg, movie_name=movie_name)
                        self._save_job_to_firestore(job)
                        gcp_logger.log_event(
                            "Ticket Booking Alert Delivered",
                            user_id=job.created_by or "system",
                            details={
                                "job_id": job.id,
                                "task_creator": creator_email,
                                "movie_name": job.movie_name,
                                "available_theatres": available,
                                "notification_medium": job.notification_medium,
                                "date_str": job.date_str
                            }
                        )
                        # Dispatch notification_sent email if channel is not email
                        if creator_email and medium_norm not in ("email",):
                            try:
                                import asyncio
                                from ..services.notification.user_mailer import send_notification_sent_email
                                user_disp = "User"
                                if job.created_by:
                                    try:
                                        from .auth import db
                                        if db:
                                            udoc = db.collection("users").document(job.created_by).get()
                                            if udoc.exists:
                                                user_disp = (udoc.to_dict() or {}).get("displayName") or user_disp
                                    except Exception:
                                        pass
                                asyncio.create_task(send_notification_sent_email(
                                    recipient_email=creator_email,
                                    user_name=user_disp,
                                    movie_name=job.movie_name,
                                    notification_medium=job.notification_medium,
                                    available_theatres=available
                                ))
                            except Exception:
                                pass
                    else:
                        job_logger.error(
                            f"⚠️ Tickets found but alert failed after {job.notification_attempt_count} attempts. Reason: {notif_msg}"
                        )
                        job.notification_status = "failed"
                        job.update_state("Error", f"{details} Alert failed: {notif_msg}", movie_name=movie_name)

                        # Auto-refund if paid and not yet refunded
                        if job.price_paise > 0 and not job.refund_issued and job.created_by:
                            try:
                                WalletService.credit(
                                    uid=job.created_by,
                                    amount_paise=job.price_paise,
                                    txn_type="JOB_REFUND",
                                    description=f"Refund for job #{job.id}: notification delivery failure",
                                    idempotency_key=f"notif_fail_refund_{job.id}",
                                    job_id=job.id,
                                    created_by="system",
                                )
                                job.refund_issued = True
                                job_logger.info(f"Wallet refund of ₹{job.price_paise/100:.2f} issued for failed job #{job.id}.")
                            except Exception as rerr:
                                job_logger.error(f"Failed to issue failure refund for job #{job.id}: {rerr}")

                        self._save_job_to_firestore(job)

                        # Dispatch notification_failed email
                        if creator_email:
                            try:
                                import asyncio
                                from ..services.notification.user_mailer import send_notification_failed_email
                                user_disp = "User"
                                if job.created_by:
                                    try:
                                        from .auth import db
                                        if db:
                                            udoc = db.collection("users").document(job.created_by).get()
                                            if udoc.exists:
                                                user_disp = (udoc.to_dict() or {}).get("displayName") or user_disp
                                    except Exception:
                                        pass
                                asyncio.create_task(send_notification_failed_email(
                                    recipient_email=creator_email,
                                    user_name=user_disp,
                                    job_id=job.id,
                                    movie_name=job.movie_name,
                                    notification_medium=job.notification_medium,
                                    error_message=notif_msg,
                                    refunded=(job.price_paise > 0 and job.refund_issued)
                                ))
                            except Exception:
                                pass

                        gcp_logger.log_event(
                            "Ticket Booking Alert Delivery Failed",
                            user_id=job.created_by or "system",
                            details={
                                "job_id": job.id,
                                "task_creator": creator_email,
                                "movie_name": job.movie_name,
                                "reason": notif_msg
                            },
                            level="ERROR"
                        )

                    # Stop monitoring once booking is successfully processed
                    break

                else:
                    job_logger.info(f"⏳  Next check in {job.check_interval} seconds...")
                    # Update state in RAM (for API responses) without writing to Firestore every loop
                    job.update_state("Running", details)

                # Responsive sleep: wake up immediately if stop is requested
                for _ in range(job.check_interval):
                    if stop_event.is_set():
                        break
                    await asyncio.sleep(1)
        finally:
            current_job_id.reset(tok_id)
            current_job_creator.reset(tok_creator)
            try:
                await scraper.close()
            except Exception:
                pass
            job_logger.info("🛑  Monitor stopped.")

