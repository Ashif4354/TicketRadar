# src/core/monitor.py

import asyncio
import threading
import time
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime

from .job import MonitorJob
from ..utils.logger import get_job_logger
from ..services.scraper.factory import ScraperFactory
from ..services.notification.factory import NotificationStrategyFactory
from ..services.gcp_logger import gcp_logger, current_job_id, current_job_creator

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
        """Upserts a MonitorJob document into the Firestore 'jobs' collection."""
        try:
            from .auth import db
            if db:
                db.collection("jobs").document(job.id).set(job.to_dict(), merge=True)
                logger.debug(f"Saved job {job.id} to Firestore.")
        except Exception as e:
            logger.error(f"Failed to save job {job.id} to Firestore: {e}")

    def _delete_job_from_firestore(self, job_id: str) -> None:
        """Deletes a job document from the Firestore 'jobs' collection."""
        try:
            from .auth import db
            if db:
                db.collection("jobs").document(job_id).delete()
                logger.info(f"Deleted job {job_id} from Firestore.")
        except Exception as e:
            logger.error(f"Failed to delete job {job_id} from Firestore: {e}")

    def _load_jobs_from_firestore(self) -> None:
        """Loads active/non-deleted jobs from the Firestore 'jobs' collection upon startup."""
        try:
            from .auth import db
            if not db:
                logger.warning("Firestore client not available. Skipping job restoration from Firestore.")
                return

            docs = db.collection("jobs").stream()
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

    def delete_job(self, job_id: str) -> bool:
        """Stops and deletes a job, cleaning up its files and references."""
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
        The main async coroutine executing the check loop.
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
                    if movie_name:
                        job.movie_name = movie_name
                except Exception as e:
                    success = False
                    details = "An unexpected error occurred during the check."
                    available, unavailable = [], job.theatres
                    job_logger.error(f"⚠️  Something went wrong during the check. Will retry. ({e})")

                if stop_event.is_set():
                    break

                if success:
                    # Attempt to send notification asynchronously
                    try:
                        notifier = NotificationStrategyFactory.create_strategy(
                            job.notification_medium,
                            job.notification_config
                        )

                        subject = f"TicketRadar: Booking Open for {job.date_str}!"

                        notif_success, notif_msg = await notifier.send_notification(
                            subject=subject,
                            movie_name=job.movie_name,
                            date_str=job.date_str,
                            available_theatres=available,
                            unavailable_theatres=unavailable,
                            url=job.url
                        )

                        if notif_success:
                            job_logger.info(
                                f"📣  Alert sent via {job.notification_medium.upper()}! "
                                f"Check your inbox / Discord."
                            )
                            status_msg = f"{details} Alert delivered."
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
                        else:
                            job_logger.error(
                                f"⚠️  Tickets found but the alert could not be delivered. "
                                f"Reason: {notif_msg}"
                            )
                            job.update_state("Error", f"{details} Alert failed: {notif_msg}", movie_name=movie_name)
                            self._save_job_to_firestore(job)
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

                    except Exception as notif_err:
                        job_logger.error(
                            f"⚠️  Tickets found but an error occurred while sending the alert. ({notif_err})"
                        )
                        job.update_state("Error", f"{details} Alert error: {str(notif_err)}", movie_name=movie_name)
                        self._save_job_to_firestore(job)

                    # Stop monitoring once booking is successfully found
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

