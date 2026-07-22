# src/Backend/api/routers/jobs.py

import json
import hashlib
import logging
from typing import List
from fastapi import APIRouter, HTTPException, BackgroundTasks, Depends
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse

from lib.utils.config import config_error
from lib.core.job import MonitorJob
from lib.core.monitor import JobManager
from lib.services.scraper.factory import ScraperFactory
from lib.services.notification import admin_notifier
from lib.services.gcp_logger import gcp_logger
from lib.core.auth import get_authorized_user
from api.schemas import CreateJobRequest
from api.dependencies import verify_recaptcha, get_user_details

logger = logging.getLogger("ticketradar.api")
manager = JobManager()

router = APIRouter(prefix="/api/jobs", tags=["Jobs"])


def get_jobs_state_hash(jobs: List[MonitorJob]) -> str:
    """Computes a deterministic hash of the current states of all jobs."""
    sorted_jobs = sorted(jobs, key=lambda j: j.id)
    state_data = []
    for job in sorted_jobs:
        state_data.append({
            "id": job.id,
            "status": job.status,
            "last_checked_at": str(job.last_checked_at) if job.last_checked_at else "",
            "last_result": job.last_result,
            "movie_name": job.movie_name
        })
    serialized = json.dumps(state_data, sort_keys=True)
    return hashlib.sha256(serialized.encode('utf-8')).hexdigest()


def verify_job_access(job_id: str, claims: dict) -> MonitorJob:
    """Verifies that the user has access to the job (owner or admin)."""
    job = manager.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail=f"Job #{job_id} not found.")

    is_admin = claims.get("role") == "admin"
    user_uid = claims.get("uid")

    if not is_admin and job.created_by != user_uid:
        raise HTTPException(
            status_code=403,
            detail="You do not have access to this job."
        )
    return job


@router.get("")
async def get_jobs(claims: dict = Depends(get_authorized_user)):
    """Returns a list of all current jobs and their states, enriched with user details for admin view."""
    is_admin = claims.get("role") == "admin"
    user_uid = claims.get("uid")

    all_jobs = manager.get_all_jobs()
    if is_admin:
        current_jobs = all_jobs
    else:
        current_jobs = [j for j in all_jobs if j.created_by == user_uid]

    user_cache = {}
    enriched_jobs = []
    for job in current_jobs:
        state = job.get_state()
        creator_uid = job.created_by
        if creator_uid:
            if creator_uid not in user_cache:
                u_name, u_email, _ = get_user_details(creator_uid)
                user_cache[creator_uid] = {"user_name": u_name, "user_email": u_email}
            state["user_name"] = user_cache[creator_uid]["user_name"]
            state["user_email"] = user_cache[creator_uid]["user_email"]
        else:
            state["user_name"] = "System"
            state["user_email"] = ""
        enriched_jobs.append(state)

    return JSONResponse(
        content=jsonable_encoder(enriched_jobs),
        headers={"Cache-Control": "no-cache, no-store, must-revalidate"}
    )


@router.post("")
async def create_job(
    payload: CreateJobRequest,
    background_tasks: BackgroundTasks,
    claims: dict = Depends(get_authorized_user)
):
    """Create and start a new monitor job."""
    if config_error:
        raise HTTPException(status_code=400, detail=f"Configuration Error: {config_error}")

    # Verify reCAPTCHA token
    await verify_recaptcha(payload.recaptcha_token)

    # Validate check interval minimum
    if payload.check_interval < 30:
        raise HTTPException(status_code=400, detail="Check interval cannot be less than 30 seconds.")

    # Validate provider
    service_provider = payload.service_provider
    try:
        scraper_cls = ScraperFactory.get_scraper_class(service_provider)
        scraper_cls.get_required_fields()
    except Exception:
        raise HTTPException(status_code=400, detail=f"Unsupported service provider: {service_provider}")

    # Validate parameters
    url = payload.params.url.strip()
    if not url.startswith("http"):
        raise HTTPException(status_code=400, detail="Enter a valid HTTP/HTTPS URL.")

    params = {
        "url": url,
        "date_str": payload.params.date_str.strip(),
        "theatres": payload.params.theatres
    }

    medium = payload.notification_medium.strip().lower()
    notif_config = {}
    if "email" in medium:
        recipient = payload.notification_config.get("recipient_email", "").strip()
        if not recipient:
            raise HTTPException(status_code=400, detail="Recipient email is required for Email notification.")
        notif_config = {"recipient_email": recipient}
        medium_name = "Email"
    else:
        webhook = payload.notification_config.get("webhook_url", "").strip()
        if not webhook:
            raise HTTPException(status_code=400, detail="Discord Webhook URL is required for Webhook notification.")
        notif_config = {"webhook_url": webhook}
        medium_name = "Discord Webhook"

    # Fetch creator details
    user_name, email, _ = get_user_details(claims.get("uid"), claims)

    # Create Monitor Job
    new_job = MonitorJob(
        params=params,
        notification_medium=medium_name,
        notification_config=notif_config,
        service_provider=service_provider,
        check_interval=payload.check_interval,
        created_by=claims.get("uid"),
        creator_email=email
    )

    success = manager.start_job(new_job)
    if success:
        background_tasks.add_task(
            admin_notifier.notify_job_created,
            new_job.id,
            new_job.movie_name,
            user_name,
            email,
            service_provider,
            new_job.theatres,
            payload.params.date_str
        )
        gcp_logger.log_event(
            "Job Created",
            user_id=claims.get("uid"),
            details={
                "job_id": new_job.id,
                "movie_name": new_job.movie_name,
                "service_provider": service_provider,
                "theatres": new_job.theatres,
                "date_str": payload.params.date_str,
                "check_interval": payload.check_interval,
                "notification_medium": medium_name,
                "user_email": email
            }
        )
        return new_job.get_state()
    else:
        raise HTTPException(status_code=500, detail="Failed to start monitoring job. An active thread might already be running.")


@router.post("/{job_id}/start")
async def start_job(job_id: str, claims: dict = Depends(get_authorized_user)):
    """Starts or restarts an existing job."""
    job = verify_job_access(job_id, claims)

    if job.status == "Running":
        return {"success": True, "message": f"Job #{job_id} is already running.", "state": job.get_state()}

    job.update_state("Idle", "Manual restart requested.")
    success = manager.start_job(job)
    if success:
        user_name, email, _ = get_user_details(claims.get("uid"), claims)
        gcp_logger.log_event(
            "Job Started",
            user_id=claims.get("uid"),
            details={
                "job_id": job.id,
                "movie_name": job.movie_name,
                "service_provider": job.service_provider,
                "user_email": email
            }
        )
        return {"success": True, "state": job.get_state()}
    else:
        raise HTTPException(status_code=500, detail="Failed to start job.")


@router.post("/{job_id}/stop")
async def stop_job(
    job_id: str,
    background_tasks: BackgroundTasks,
    claims: dict = Depends(get_authorized_user)
):
    """Stops a running job."""
    job = verify_job_access(job_id, claims)
    success = manager.stop_job(job_id)
    if success:
        user_name, email, _ = get_user_details(claims.get("uid"), claims)
        background_tasks.add_task(
            admin_notifier.notify_job_stopped,
            job.id,
            job.movie_name,
            user_name,
            email,
            job.service_provider,
            job.theatres,
            job.date_str
        )
        gcp_logger.log_event(
            "Job Stopped",
            user_id=claims.get("uid"),
            details={
                "job_id": job.id,
                "movie_name": job.movie_name,
                "service_provider": job.service_provider,
                "user_email": email
            }
        )
        return {"success": True, "message": f"Job #{job_id} stopped."}
    else:
        raise HTTPException(status_code=404, detail=f"Job #{job_id} not found or could not be stopped.")


@router.delete("/{job_id}")
async def delete_job(
    job_id: str,
    background_tasks: BackgroundTasks,
    claims: dict = Depends(get_authorized_user)
):
    """Deletes a job."""
    job = verify_job_access(job_id, claims)
    success = manager.delete_job(job_id)
    if success:
        user_name, email, _ = get_user_details(claims.get("uid"), claims)
        background_tasks.add_task(
            admin_notifier.notify_job_deleted,
            job.id,
            job.movie_name,
            user_name,
            email,
            job.service_provider,
            job.theatres,
            job.date_str
        )
        gcp_logger.log_event(
            "Job Deleted",
            user_id=claims.get("uid"),
            details={
                "job_id": job.id,
                "movie_name": job.movie_name,
                "service_provider": job.service_provider,
                "user_email": email
            }
        )
        return {"success": True, "message": f"Job #{job_id} deleted."}
    else:
        raise HTTPException(status_code=404, detail=f"Job #{job_id} not found.")
