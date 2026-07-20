# src/core/monitor.py

import asyncio
import threading
import time
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime

from src.core.job import MonitorJob
from src.logger import get_job_logger, delete_job_log_file
from src.services.scraper.factory import ScraperFactory
from src.services.notification.factory import NotificationStrategyFactory

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

    def _run_async_loop(self, loop: asyncio.AbstractEventLoop) -> None:
        """Runs the asyncio event loop forever in a background thread."""
        asyncio.set_event_loop(loop)
        loop.run_forever()

    async def _create_event(self) -> asyncio.Event:
        """Helper coroutine to create an Event on the loop thread."""
        return asyncio.Event()

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
                
        # Delete the job log file
        delete_job_log_file(job_id)
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

        try:
            while not stop_event.is_set():
                job_logger.info("🔄  Checking availability on BookMyShow...")

                # Perform scraping check asynchronously
                try:
                    success, details, movie_name, available, unavailable = await scraper.check_booking(
                        job.params,
                        headless=job.headless,
                        keep_browser_open=job.keep_browser_open,
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
                            job.update_state("Success", f"{details} Alert delivered.", movie_name=movie_name)
                        else:
                            job_logger.error(
                                f"⚠️  Tickets found but the alert could not be delivered. "
                                f"Reason: {notif_msg}"
                            )
                            job.update_state("Error", f"{details} Alert failed: {notif_msg}", movie_name=movie_name)

                    except Exception as notif_err:
                        job_logger.error(
                            f"⚠️  Tickets found but an error occurred while sending the alert. ({notif_err})"
                        )
                        job.update_state("Error", f"{details} Alert error: {str(notif_err)}", movie_name=movie_name)

                    # Stop monitoring once booking is successfully found
                    break

                else:
                    job_logger.info(f"⏳  Next check in {job.check_interval} seconds...")
                    job.update_state("Running", details)

                # Responsive sleep: wake up immediately if stop is requested
                for _ in range(job.check_interval):
                    if stop_event.is_set():
                        break
                    await asyncio.sleep(1)
        finally:
            try:
                await scraper.close()
            except Exception:
                pass
            job_logger.info("🛑  Monitor stopped.")

