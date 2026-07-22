# src/Backend/main.py

import os
import sys
import asyncio
import logging
from contextlib import asynccontextmanager
from typing import Dict, Any, List

# Ensure the project root directory is in Python path to support src.Backend imports
backend_dir = os.path.dirname(os.path.abspath(__file__))
root_dir = os.path.abspath(os.path.join(backend_dir, "..", ".."))
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

import json
import hashlib
import httpx
from fastapi import FastAPI, HTTPException, BackgroundTasks, Depends, Header  # noqa: E402, F401
from fastapi.encoders import jsonable_encoder
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from src.Backend.config import settings, config_error
from src.Backend.core.job import MonitorJob
from src.Backend.core.monitor import JobManager
from src.Backend.services.notification.factory import NotificationStrategyFactory
from src.Backend.services.scraper.factory import ScraperFactory
from src.Backend.logger import get_job_logs_user
from src.Backend.core.auth import (
    get_current_user_claims,
    get_authorized_user,
    get_admin_user,
    db,
    auth as firebase_auth
)

# Initialize logger
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("ticketradar.api")

# Get JobManager instance (singleton)
manager = JobManager()

# Pydantic models for request/response validation
class TestAlertRequest(BaseModel):
    medium: str = Field(..., description="Alert medium: 'email' or 'discord'")
    target: str = Field(..., description="Target email address or webhook URL")
    recaptcha_token: str = Field(..., description="Google reCAPTCHA token")


class JobParams(BaseModel):
    url: str
    date_str: str
    theatres: List[str]

class CreateJobRequest(BaseModel):
    service_provider: str = "BookMyShow"
    notification_medium: str
    notification_config: Dict[str, Any]
    check_interval: int = 30
    params: JobParams
    recaptcha_token: str = Field(..., description="Google reCAPTCHA token")

async def verify_recaptcha(token: str):
    """Verifies a reCAPTCHA v2 token with Google's siteverify API."""
    if not token:
        raise HTTPException(status_code=400, detail="reCAPTCHA token is required.")
        
    recaptcha_url = "https://www.google.com/recaptcha/api/siteverify"
    secret_key = settings.recaptcha_secret if settings else "6LfUdl0tAAAAAAjyjVtoGRY2cY52NJUOhc4R3mLu"
    
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                recaptcha_url,
                data={
                    "secret": secret_key,
                    "response": token
                }
            )
            resp_data = resp.json()
            if not resp_data.get("success"):
                logger.warning(f"reCAPTCHA validation failed: {resp_data}")
                raise HTTPException(status_code=400, detail="reCAPTCHA verification failed.")
    except httpx.HTTPError as e:
        logger.error(f"reCAPTCHA verification request failed: {e}")
        raise HTTPException(status_code=500, detail="Unable to verify reCAPTCHA with Google servers.")

@asynccontextmanager
async def lifespan(app: FastAPI):
    yield
    
    # Shutdown: Stop all running jobs on exit
    logger.info("Shutting down backend app...")
    for job in manager.get_all_jobs():
        manager.stop_job(job.id)

app = FastAPI(
    title="TicketRadar API",
    description="Backend API for TicketRadar movie ticket monitoring",
    version="0.1.0",
    lifespan=lifespan
)

# Enable CORS for development (allowing localhost proxy)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/api/config")
async def get_config():
    """Retrieve application configuration and validation error status."""
    return {
        "config_error": config_error,
        "smtp_server": settings.smtp_server if settings else None,
        "smtp_email": settings.smtp_email if settings else None,
        "default_check_interval": settings.default_check_interval if settings else 30
    }

@app.post("/api/test-notification")
async def test_notification(payload: TestAlertRequest, claims: dict = Depends(get_authorized_user)):
    """Sends a test alert to verify connection details."""
    medium = payload.medium.lower()
    target = payload.target.strip()
    
    if not target:
        raise HTTPException(status_code=400, detail="Target recipient/URL is required.")
        
    # Verify reCAPTCHA token
    await verify_recaptcha(payload.recaptcha_token)

        
    if "email" in medium:
        config = {"recipient_email": target}
        notif_type = "email"
    elif "discord" in medium:
        config = {"webhook_url": target}
        notif_type = "discord"
    else:
        raise HTTPException(status_code=400, detail=f"Unsupported notification medium: {payload.medium}")
        
    try:
        notifier = NotificationStrategyFactory.create_strategy(notif_type, config)
        success, msg = await notifier.send_notification(
            subject="Test Alert",
            movie_name="Test Movie",
            date_str="20260719",
            available_theatres=["Sample Theatre A", "Sample Theatre B"],
            unavailable_theatres=["Sample Theatre C"],
            url="https://in.bookmyshow.com"
        )
        if success:
            return {"success": True, "message": "Test notification sent successfully!"}
        else:
            return {"success": False, "message": msg}
    except Exception as err:
        return {"success": False, "message": str(err)}

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

@app.get("/api/jobs")
async def get_jobs(
    version: str = None,
    timeout: int = 10,
    claims: dict = Depends(get_authorized_user)
):
    """Returns a list of all current jobs and their states.
    Supports long polling if 'version' parameter is provided.
    """
    start_time = asyncio.get_event_loop().time()
    is_admin = claims.get("role") == "admin"
    user_uid = claims.get("uid")
    
    while True:
        all_jobs = manager.get_all_jobs()
        if is_admin:
            current_jobs = all_jobs
        else:
            current_jobs = [j for j in all_jobs if j.created_by == user_uid]
            
        current_hash = get_jobs_state_hash(current_jobs)
        
        # If version is not provided or it doesn't match the current hash, return immediately
        if not version or current_hash != version:
            headers = {
                "X-State-Version": current_hash,
                "Cache-Control": "no-cache, no-store, must-revalidate"
            }
            return JSONResponse(
                content=jsonable_encoder([job.get_state() for job in current_jobs]),
                headers=headers
            )
            
        # Check if timeout is reached
        elapsed = asyncio.get_event_loop().time() - start_time
        if elapsed >= timeout:
            headers = {
                "X-State-Version": current_hash,
                "Cache-Control": "no-cache, no-store, must-revalidate"
            }
            return JSONResponse(
                content=jsonable_encoder([job.get_state() for job in current_jobs]),
                headers=headers
            )
            
        # Wait a short duration before checking again
        await asyncio.sleep(0.5)

@app.post("/api/jobs")
async def create_job(payload: CreateJobRequest, claims: dict = Depends(get_authorized_user)):
    """Create and start a new monitor job."""
    if config_error:
        raise HTTPException(status_code=400, detail=f"Configuration Error: {config_error}")
        
    # Verify reCAPTCHA token
    await verify_recaptcha(payload.recaptcha_token)

        
    # Validate provider
    service_provider = payload.service_provider
    try:
        scraper_cls = ScraperFactory.get_scraper_class(service_provider)
        fields = scraper_cls.get_required_fields()
    except Exception as e:
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
        
    # Create Monitor Job
    new_job = MonitorJob(
        params=params,
        notification_medium=medium_name,
        notification_config=notif_config,
        service_provider=service_provider,
        check_interval=payload.check_interval,
        created_by=claims.get("uid")
    )
    
    success = manager.start_job(new_job)
    if success:
        return new_job.get_state()
    else:
        raise HTTPException(status_code=500, detail="Failed to start monitoring job. An active thread might already be running.")

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

@app.post("/api/jobs/{job_id}/start")
async def start_job(job_id: str, claims: dict = Depends(get_authorized_user)):
    """Starts or restarts an existing job."""
    job = verify_job_access(job_id, claims)
        
    if job.status == "Running":
        return {"success": True, "message": f"Job #{job_id} is already running.", "state": job.get_state()}
        
    job.update_state("Idle", "Manual restart requested.")
    success = manager.start_job(job)
    if success:
        return {"success": True, "state": job.get_state()}
    else:
        raise HTTPException(status_code=500, detail="Failed to start job.")

@app.post("/api/jobs/{job_id}/stop")
async def stop_job(job_id: str, claims: dict = Depends(get_authorized_user)):
    """Stops a running job."""
    verify_job_access(job_id, claims)
    success = manager.stop_job(job_id)
    if success:
        return {"success": True, "message": f"Job #{job_id} stopped."}
    else:
        raise HTTPException(status_code=404, detail=f"Job #{job_id} not found or could not be stopped.")

@app.delete("/api/jobs/{job_id}")
async def delete_job(job_id: str, claims: dict = Depends(get_authorized_user)):
    """Deletes a job."""
    verify_job_access(job_id, claims)
    success = manager.delete_job(job_id)
    if success:
        return {"success": True, "message": f"Job #{job_id} deleted."}
    else:
        raise HTTPException(status_code=404, detail=f"Job #{job_id} not found.")

@app.get("/api/jobs/{job_id}/logs")
async def get_logs(job_id: str, tail: int = 60, claims: dict = Depends(get_authorized_user)):
    """Retrieves user-facing logs for a specific job."""
    verify_job_access(job_id, claims)
    logs = get_job_logs_user(job_id, tail_lines=tail)
    return {"job_id": job_id, "logs": logs}


# Admin router and public request-access API
from fastapi import APIRouter
from google.cloud import firestore as google_firestore

admin_router = APIRouter(
    prefix="/admin",
    dependencies=[Depends(get_admin_user)]
)

class UpdateRoleRequest(BaseModel):
    role: str

@admin_router.get("/users")
async def admin_list_users():
    """Lists all users from Firebase Authentication."""
    try:
        page = firebase_auth.list_users()
        users_list = []
        for u in page.users:
            users_list.append({
                "uid": u.uid,
                "email": u.email,
                "displayName": u.display_name,
                "photoUrl": u.photo_url,
                "disabled": u.disabled,
                "custom_claims": u.custom_claims or {}
            })
        return users_list
    except Exception as e:
        logger.error(f"Error listing users: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@admin_router.post("/users/{uid}/role")
async def admin_update_role(uid: str, payload: UpdateRoleRequest):
    """Updates the user's role claim (admin or user)."""
    if payload.role not in ["admin", "user"]:
        raise HTTPException(status_code=400, detail="Invalid role. Must be 'admin' or 'user'.")
    try:
        user = firebase_auth.get_user(uid)
        claims = user.custom_claims or {}
        claims["role"] = payload.role
        firebase_auth.set_custom_user_claims(uid, claims)
        return {"success": True, "message": f"User role updated to {payload.role}."}
    except Exception as e:
        logger.error(f"Error updating role: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@admin_router.post("/users/{uid}/block")
async def admin_block_user(uid: str):
    """Sets the 'blocked' claim to True."""
    try:
        user = firebase_auth.get_user(uid)
        claims = user.custom_claims or {}
        claims["blocked"] = True
        firebase_auth.set_custom_user_claims(uid, claims)
        return {"success": True, "message": "User blocked successfully."}
    except Exception as e:
        logger.error(f"Error blocking user: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@admin_router.post("/users/{uid}/unblock")
async def admin_unblock_user(uid: str):
    """Sets the 'blocked' claim to False."""
    try:
        user = firebase_auth.get_user(uid)
        claims = user.custom_claims or {}
        claims["blocked"] = False
        firebase_auth.set_custom_user_claims(uid, claims)
        return {"success": True, "message": "User unblocked successfully."}
    except Exception as e:
        logger.error(f"Error unblocking user: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@admin_router.get("/requests")
async def admin_list_requests():
    """Lists all access requests from Firestore."""
    if db is None:
        raise HTTPException(status_code=500, detail="Firestore is not available.")
    try:
        requests_ref = db.collection("access_requests").order_by("requested_at", direction=google_firestore.Query.DESCENDING)
        docs = requests_ref.stream()
        reqs = []
        for doc in docs:
            data = doc.to_dict()
            if "requested_at" in data and data["requested_at"]:
                data["requested_at"] = data["requested_at"].isoformat()
            if "approved_at" in data and data["approved_at"]:
                data["approved_at"] = data["approved_at"].isoformat()
            if "denied_at" in data and data["denied_at"]:
                data["denied_at"] = data["denied_at"].isoformat()
            reqs.append(data)
        return reqs
    except Exception as e:
        logger.error(f"Error listing access requests: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@admin_router.post("/requests/{uid}/approve")
async def admin_approve_request(uid: str):
    """Approves an access request, sets 'authorized=True', and updates Firestore."""
    try:
        user = firebase_auth.get_user(uid)
        claims = user.custom_claims or {}
        claims["authorized"] = True
        if "role" not in claims:
            claims["role"] = "user"
        firebase_auth.set_custom_user_claims(uid, claims)

        if db is not None:
            db.collection("access_requests").document(uid).update({
                "status": "approved",
                "approved_at": google_firestore.SERVER_TIMESTAMP
            })
        return {"success": True, "message": "Access request approved successfully."}
    except Exception as e:
        logger.error(f"Error approving access request: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@admin_router.post("/requests/{uid}/deny")
async def admin_deny_request(uid: str):
    """Denies an access request (updates Firestore to 'denied')."""
    try:
        if db is not None:
            db.collection("access_requests").document(uid).update({
                "status": "denied",
                "denied_at": google_firestore.SERVER_TIMESTAMP
            })
        return {"success": True, "message": "Access request denied."}
    except Exception as e:
        logger.error(f"Error denying access request: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@admin_router.post("/jobs/{job_id}/stop")
async def admin_stop_job(job_id: str):
    """Stops any running job."""
    success = manager.stop_job(job_id)
    if success:
        return {"success": True, "message": f"Job #{job_id} stopped."}
    else:
        raise HTTPException(status_code=404, detail=f"Job #{job_id} not found or could not be stopped.")

@admin_router.delete("/jobs/{job_id}")
async def admin_delete_job(job_id: str):
    """Deletes any job."""
    success = manager.delete_job(job_id)
    if success:
        return {"success": True, "message": f"Job #{job_id} deleted."}
    else:
        raise HTTPException(status_code=404, detail=f"Job #{job_id} not found.")

app.include_router(admin_router)

class RequestAccessPayload(BaseModel):
    recaptcha_token: str

@app.post("/api/request-access")
async def request_access(payload: RequestAccessPayload, claims: dict = Depends(get_current_user_claims)):
    """Submits a request access form to Firestore."""
    await verify_recaptcha(payload.recaptcha_token)
    
    if db is None:
        raise HTTPException(status_code=500, detail="Firestore is not configured.")
        
    uid = claims.get("uid")
    email = claims.get("email")
    display_name = claims.get("name", "")
    
    # Check if already has a pending request
    doc_ref = db.collection("access_requests").document(uid)
    doc = doc_ref.get()
    if doc.exists:
        data = doc.to_dict()
        if data.get("status") == "pending":
            return {"success": True, "message": "Access request already pending."}
            
    doc_ref.set({
        "uid": uid,
        "email": email,
        "displayName": display_name,
        "status": "pending",
        "requested_at": google_firestore.SERVER_TIMESTAMP
    })
    
    return {"success": True, "message": "Access request submitted successfully."}


# Serve React Frontend Static Files
# Resolve the UI/dist folder path
if hasattr(sys, "_MEIPASS"):
    # PyInstaller single-exe temp directory
    ui_dist_dir = os.path.join(sys._MEIPASS, "src", "UI", "dist")
else:
    # Dev/Standard run: relative to this file (src/Backend/main.py)
    ui_dist_dir = os.path.abspath(os.path.join(backend_dir, "..", "UI", "dist"))

# Check if front-end files exist, if so mount them
if os.path.exists(ui_dist_dir):
    app.frontend("/", directory=ui_dist_dir, fallback="index.html")
    logger.info(f"Mounted frontend static files from: {ui_dist_dir} via app.frontend")
else:
    logger.warning(f"Frontend static files directory not found at: {ui_dist_dir}. Serving API only.")

# Fallback root route if static directory is missing
@app.get("/")
async def root_fallback():
    return JSONResponse(
        status_code=200,
        content={"message": "TicketRadar API is active. Frontend static files are not built yet."}
    )

if __name__ == "__main__":
    import uvicorn
    # If run as standalone, launch via uvicorn
    # Use reload only when not compiled
    is_frozen = getattr(sys, "frozen", False) or "__compiled__" in globals()
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=not is_frozen)
