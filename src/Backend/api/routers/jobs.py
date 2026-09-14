import json
import hashlib
import logging
import os
import uuid
from typing import List, Any
from fastapi import APIRouter, HTTPException, BackgroundTasks, Depends
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse

from lib.utils.config import config_error, settings
from lib.core.job import MonitorJob
from lib.core.monitor import JobManager
from lib.services.scraper.factory import ScraperFactory
from lib.services.notification import admin_notifier
from lib.services.notification.user_mailer import send_job_created_email
from lib.services.gcp_logger import gcp_logger
from lib.core.auth import get_authorized_user, db
from lib.utils.phone import normalize_indian_phone
from lib.services.pricing import PricingService
from lib.services.wallet import WalletService, InsufficientFundsError
from api.schemas import CreateJobRequest, UpdateJobRequest, JobParams
from api.dependencies import verify_recaptcha, get_user_details, require_terms_accepted

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


import re

def validate_job_url(service_provider: str, raw_url: str) -> str:
    """
    Validate and normalize a job URL for the specified service provider.
    
    Parameters:
        service_provider (str): Provider whose URL format should be validated.
        raw_url (str): URL to trim and validate.
    
    Returns:
        str: The trimmed HTTPS URL.
    
    Raises:
        HTTPException: If the URL is not HTTPS or does not match the required
            BookMyShow format.
    """
    url = raw_url.strip()
    if not url.startswith("https://"):
        raise HTTPException(status_code=400, detail="Enter a valid HTTPS URL.")

    sp_lower = service_provider.lower().replace(" ", "").replace("-", "")
    if "bookmyshow" in sp_lower:
        pattern = r'^https://(?:[a-zA-Z0-9-]+\.)*bookmyshow\.com/(?:movies/[^/]+/[^/]+|buytickets/[^/]+)'
        if not re.match(pattern, url, re.IGNORECASE):
            raise HTTPException(
                status_code=400,
                detail="Enter a valid BookMyShow movie link."
            )
    return url


def _extract_job_params(job_params: JobParams | Any, url: str) -> dict:
    """
    Extract and structure job parameters dictionary from a JobParams object or dict,
    ensuring the validated URL is included.
    """
    if isinstance(job_params, dict):
        params_dict = dict(job_params)
    elif hasattr(job_params, "model_dump"):
        params_dict = job_params.model_dump()
    elif hasattr(job_params, "dict"):
        params_dict = job_params.dict()
    else:
        params_dict = dict(job_params)

    params_dict["url"] = url
    return params_dict




def verify_job_access(job_id: str, claims: dict) -> MonitorJob:
    """
    Verify that the authenticated user can access the specified job.
    
    Parameters:
        job_id (str): Identifier of the job to retrieve.
        claims (dict): Authenticated user claims, including the user ID and role.
    
    Returns:
        MonitorJob: The requested job.
    
    Raises:
        HTTPException: If the job does not exist or the user lacks access.
    """
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
async def get_jobs(all: bool = False, claims: dict = Depends(get_authorized_user)):
    """Returns a list of current jobs. By default returns only the user's own jobs. If all=True and user is admin, returns all jobs."""
    is_admin = claims.get("role") == "admin"
    user_uid = claims.get("uid")

    if all and not is_admin:
        raise HTTPException(
            status_code=403,
            detail="Forbidden: Only administrators are permitted to use parameter all=true."
        )

    all_jobs = manager.get_all_jobs()
    if is_admin and all:
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
    """
    Create and start a monitoring job for the authenticated user.
    
    Parameters:
    	payload (CreateJobRequest): Job configuration, monitoring parameters, and notification settings.
    	background_tasks (BackgroundTasks): Tasks used for post-creation notifications.
    	claims (dict): Authenticated user claims.
    
    Returns:
    	dict: The newly created job's current state.
    """
    if config_error:
        raise HTTPException(status_code=400, detail=f"Configuration Error: {config_error}")

    # Verify reCAPTCHA token
    await verify_recaptcha(payload.recaptcha_token)

    # Validate check interval minimum (minimum 1 minute / 60 seconds)
    if payload.check_interval < 60:
        raise HTTPException(status_code=400, detail="Check interval cannot be less than 1 minute (60 seconds).")

    # Validate provider
    service_provider = payload.service_provider
    try:
        scraper_cls = ScraperFactory.get_scraper_class(service_provider)
        scraper_cls.get_required_fields()
    except Exception:
        raise HTTPException(status_code=400, detail=f"Unsupported service provider: {service_provider}")

    # Check terms acceptance
    await require_terms_accepted(claims)

    # Validate parameters
    url = validate_job_url(service_provider, payload.params.url)
    params = _extract_job_params(payload.params, url)

    medium_raw = payload.notification_medium.strip().lower().replace(" ", "_")
    notif_config = dict(payload.notification_config)
    phone = payload.phone_number

    if "email" in medium_raw:
        recipient = payload.notification_config.get("recipient_email", "").strip()
        if not recipient:
            raise HTTPException(status_code=400, detail="Recipient email is required for Email notification.")
        notif_config = {"recipient_email": recipient}
        medium_name = "Email"
        if db:
            c_doc = db.collection("notification_consents").document(claims.get("uid")).get()
            cdata = c_doc.to_dict() or {} if c_doc.exists else {}
            if not (payload.email_consent or cdata.get("email_consented")):
                raise HTTPException(status_code=400, detail="Email consent is required. Please opt-in in your Profile.")
    elif "discord" in medium_raw:
        webhook = payload.notification_config.get("webhook_url", "").strip()
        if not webhook:
            raise HTTPException(status_code=400, detail="Discord Webhook URL is required for Webhook notification.")
        notif_config = {"webhook_url": webhook}
        medium_name = "Discord Webhook"
        if db:
            c_doc = db.collection("notification_consents").document(claims.get("uid")).get()
            cdata = c_doc.to_dict() or {} if c_doc.exists else {}
            if not (payload.discord_consent or cdata.get("discord_consented")):
                raise HTTPException(status_code=400, detail="Discord consent is required. Please opt-in in your Profile.")
    elif medium_raw in ("sms", "whatsapp", "phone_call", "call"):
        phone_input = phone or payload.notification_config.get("phone_number") or payload.notification_config.get("phone", "")
        if not phone_input:
            raise HTTPException(status_code=400, detail="Phone number is required for SMS, WhatsApp, and Phone Call.")
        try:
            phone = normalize_indian_phone(phone_input)
            notif_config["phone_number"] = phone
        except ValueError as ve:
            raise HTTPException(status_code=400, detail=str(ve))

        # Check consent in Firestore if available
        if db:
            c_doc = db.collection("notification_consents").document(claims.get("uid")).get()
            cdata = c_doc.to_dict() or {} if c_doc.exists else {}
            if medium_raw == "whatsapp" and not (payload.whatsapp_consent or cdata.get("whatsapp_consented")):
                raise HTTPException(status_code=400, detail="WhatsApp consent is required. Please opt-in in your Profile.")
            elif medium_raw == "sms" and not (payload.sms_consent or cdata.get("sms_consented")):
                raise HTTPException(status_code=400, detail="SMS consent is required. Please opt-in in your Profile.")
            elif medium_raw in ("phone_call", "call") and not (payload.call_consent or cdata.get("call_consented")):
                raise HTTPException(status_code=400, detail="Phone Call consent is required. Please opt-in in your Profile.")

        if medium_raw == "sms":
            medium_name = "SMS"
        elif medium_raw == "whatsapp":
            medium_name = "WhatsApp"
        else:
            medium_name = "Phone Call"
    else:
        raise HTTPException(status_code=400, detail=f"Unsupported notification medium: {payload.notification_medium}")

    # Fetch creator details
    user_name, email, _ = get_user_details(claims.get("uid"), claims)

    # Pricing & Payment handling
    disable_payments = (
        os.getenv("DISABLE_PAYMENTS", "").lower() in ("true", "1")
        or (settings and getattr(settings, "disable_payments", False))
    )

    price_paise = 0
    price_config_id = None
    payment_method = "free" if disable_payments else payload.payment_method.lower()

    temp_job_id = str(uuid.uuid4())[:8]
    debited_wallet = False

    if not disable_payments:
        price_paise, price_config_id = PricingService.get_price_for_medium(medium_name)
        if price_paise > 0:
            if payment_method == "wallet":
                idempotency_key = f"job_pay_{temp_job_id}"
                try:
                    WalletService.debit(
                        uid=claims.get("uid"),
                        amount_paise=price_paise,
                        txn_type="JOB_PAYMENT",
                        description=f"Payment for {medium_name} monitor #{temp_job_id}",
                        idempotency_key=idempotency_key,
                        job_id=temp_job_id,
                        created_by=f"user:{claims.get('uid')}",
                    )
                    debited_wallet = True
                except InsufficientFundsError as ife:
                    raise HTTPException(status_code=402, detail=str(ife))
            elif payment_method in ("cashfree", "gateway"):
                raise HTTPException(
                    status_code=400,
                    detail="For direct online gateway payment, initiate checkout via /api/payments/job/initiate."
                )
            else:
                payment_method = "wallet"

    # Create Monitor Job
    new_job = MonitorJob(
        params=params,
        notification_medium=medium_name,
        notification_config=notif_config,
        service_provider=service_provider,
        check_interval=payload.check_interval,
        created_by=claims.get("uid"),
        creator_email=email,
        phone_number=phone if medium_raw in ("sms", "whatsapp", "phone_call", "call") else None,
        sms_consent=payload.sms_consent,
        call_consent=payload.call_consent,
        payment_method=payment_method,
        price_paise=price_paise,
        price_config_id=price_config_id,
        job_id=temp_job_id,
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
        if email:
            background_tasks.add_task(
                send_job_created_email,
                email,
                user_name,
                new_job.id,
                new_job.movie_name,
                payload.params.date_str,
                new_job.theatres,
                medium_name,
                payload.check_interval
            )
            if debited_wallet and price_paise > 0:
                from lib.services.notification.user_mailer import send_wallet_transaction_email
                background_tasks.add_task(
                    send_wallet_transaction_email,
                    email,
                    user_name,
                    "JOB_PAYMENT",
                    "DEBIT",
                    round(price_paise / 100.0, 2),
                    round(WalletService.get_balance(claims.get("uid")) / 100.0, 2),
                    f"Ticket monitor #{new_job.id} creation fee"
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
                "payment_method": payment_method,
                "price_paise": price_paise,
                "user_email": email
            }
        )
        return new_job.get_state()
    else:
        # Rollback wallet debit if started failed
        if debited_wallet:
            try:
                WalletService.credit(
                    uid=claims.get("uid"),
                    amount_paise=price_paise,
                    txn_type="JOB_REFUND",
                    description=f"Auto-rollback for failed start of job #{temp_job_id}",
                    idempotency_key=f"cancel_job_pay_rollback_{temp_job_id}",
                    job_id=temp_job_id,
                )
            except Exception as rollback_err:
                logger.error(f"Failed to rollback wallet debit for {temp_job_id}: {rollback_err}")

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

    claim_res = manager.claim_cancellation(job_id)
    if not claim_res.get("ok"):
        raise HTTPException(
            status_code=409,
            detail="Notification is currently being dispatched. Cannot cancel now."
        )

    refund_eligible = claim_res.get("refund", False)
    success = manager.delete_job(job_id, refund_eligible=refund_eligible)
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
        if email:
            from lib.services.notification.user_mailer import send_job_cancelled_email, send_refund_email
            refund_amt = round(job.price_paise / 100.0, 2) if (refund_eligible and job.price_paise > 0) else 0.0
            background_tasks.add_task(send_job_cancelled_email, email, user_name, job.id, job.movie_name, refund_amt)
            if refund_amt > 0:
                background_tasks.add_task(send_refund_email, email, user_name, refund_amt, f"Job #{job.id} cancelled before alert dispatch", job.id)

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


@router.put("/{job_id}")
async def update_job(
    job_id: str,
    payload: UpdateJobRequest,
    claims: dict = Depends(get_authorized_user)
):
    """
    Update a monitor job owned by the authenticated user and apply its new monitoring configuration.
    """
    job = verify_job_access(job_id, claims)
    if not job:
        raise HTTPException(status_code=404, detail=f"Job #{job_id} not found.")

    user_uid = claims.get("uid")
    # Admin is explicitly prohibited from editing other users' jobs
    if job.created_by != user_uid:
        raise HTTPException(
            status_code=403,
            detail="Forbidden: You are only permitted to edit jobs created by yourself."
        )

    # Validate check interval minimum (minimum 1 minute / 60 seconds)
    if payload.check_interval < 60:
        raise HTTPException(status_code=400, detail="Check interval cannot be less than 1 minute (60 seconds).")

    # Validate provider
    service_provider = payload.service_provider
    try:
        scraper_cls = ScraperFactory.get_scraper_class(service_provider)
        scraper_cls.get_required_fields()
    except Exception:
        raise HTTPException(status_code=400, detail=f"Unsupported service provider: {service_provider}")

    # Validate parameters
    url = validate_job_url(service_provider, payload.params.url)

    params = _extract_job_params(payload.params, url)

    medium = payload.notification_medium.strip().lower().replace(" ", "_")
    notif_config = {}
    phone = None

    if "email" in medium:
        recipient = payload.notification_config.get("recipient_email", "").strip()
        if not recipient:
            raise HTTPException(status_code=400, detail="Recipient email is required for Email notification.")
        notif_config = {"recipient_email": recipient}
        medium_name = "Email"
    elif "discord" in medium:
        webhook = payload.notification_config.get("webhook_url", "").strip()
        if not webhook:
            raise HTTPException(status_code=400, detail="Discord Webhook URL is required for Webhook notification.")
        notif_config = {"webhook_url": webhook}
        medium_name = "Discord Webhook"
    elif medium in ("sms", "whatsapp", "phone_call", "call"):
        phone_input = (
            payload.notification_config.get("phone_number")
            or payload.notification_config.get("phone")
            or getattr(payload, "phone_number", None)
            or job.phone_number
        )
        if not phone_input:
            raise HTTPException(status_code=400, detail="Phone number is required for SMS, WhatsApp, and Phone Call.")
        try:
            phone = normalize_indian_phone(str(phone_input))
            notif_config = {"phone_number": phone}
        except ValueError as ve:
            raise HTTPException(status_code=400, detail=str(ve))

        if medium == "sms":
            medium_name = "SMS"
        elif medium == "whatsapp":
            medium_name = "WhatsApp"
        else:
            medium_name = "Phone Call"
    else:
        raise HTTPException(status_code=400, detail=f"Unsupported notification medium: {payload.notification_medium}")

    was_running = (job.status == "Running")

    # Update job internal data
    job.update_data(
        params=params,
        notification_medium=medium_name,
        notification_config=notif_config,
        service_provider=service_provider,
        check_interval=payload.check_interval,
        phone_number=phone,
    )

    if was_running:
        # Stop existing background loop
        manager.stop_job(job_id)
        job.update_state("Idle", "Job updated — restarting monitor with new data...")
        manager._save_job_to_firestore(job)
        # Restart immediately with new data
        success = manager.start_job(job)
        if not success:
            logger.warning(f"Job #{job_id} updated while running, but automatic restart failed.")
    else:
        job.update_state("Stopped", "Job parameters updated. Click Resume Alert to start monitoring.")
        manager._save_job_to_firestore(job)

    user_name, email, _ = get_user_details(user_uid, claims)
    gcp_logger.log_event(
        "Job Updated",
        user_id=user_uid,
        details={
            "job_id": job.id,
            "movie_name": job.movie_name,
            "service_provider": service_provider,
            "was_running": was_running,
            "user_email": email
        }
    )

    return {"success": True, "message": "Job updated successfully.", "state": job.get_state()}
