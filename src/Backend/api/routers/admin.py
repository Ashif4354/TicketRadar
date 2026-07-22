# src/Backend/api/routers/admin.py

import logging
from fastapi import APIRouter, HTTPException, BackgroundTasks, Depends
from google.cloud import firestore as google_firestore

from lib.core.auth import get_admin_user, db, auth as firebase_auth
from lib.core.monitor import JobManager
from lib.services.notification import admin_notifier
from lib.services.gcp_logger import gcp_logger
from api.schemas import UpdateRoleRequest
from api.dependencies import get_user_details

logger = logging.getLogger("ticketradar.api")
manager = JobManager()

router = APIRouter(
    prefix="/admin",
    tags=["Admin"],
    dependencies=[Depends(get_admin_user)]
)


@router.get("/counts")
async def admin_get_counts():
    """Returns lightweight counts for requests, users, and jobs without pulling heavy user claim data."""
    try:
        req_count = 0
        if db is not None:
            try:
                docs = db.collection("access_requests").where("status", "==", "pending").stream()
                req_count = sum(1 for _ in docs)
            except Exception as fe:
                logger.warning(f"Error counting pending requests: {fe}")

        page = firebase_auth.list_users()
        user_count = len(page.users)

        jobs_count = len(manager.get_all_jobs())

        return {
            "requests": req_count,
            "users": user_count,
            "jobs": jobs_count
        }
    except Exception as e:
        logger.error(f"Error fetching admin counts: {e}")
        return {"requests": 0, "users": 0, "jobs": 0}


@router.get("/users")
async def admin_list_users():
    """Lists all users from Firebase Authentication enriched with exact access status from Firestore DB & Claims."""
    try:
        access_req_map = {}
        if db is not None:
            try:
                docs = db.collection("access_requests").stream()
                for doc in docs:
                    data = doc.to_dict() or {}
                    status = data.get("status")
                    uid = data.get("uid")
                    if uid:
                        access_req_map[uid] = status
                    access_req_map[doc.id] = status
            except Exception as firestore_err:
                logger.warning(f"Could not fetch access requests for user status: {firestore_err}")

        page = firebase_auth.list_users()
        users_list = []
        for u in page.users:
            claims = u.custom_claims or {}
            db_status = access_req_map.get(u.uid)

            if claims.get("blocked") is True or db_status == "blocked":
                access_status = "blocked"
            elif claims.get("role") == "admin" or claims.get("authorized") is True or db_status == "approved":
                access_status = "authorized"
            elif db_status == "pending":
                access_status = "pending"
            elif db_status == "denied":
                access_status = "denied"
            else:
                access_status = "not yet requested"

            users_list.append({
                "uid": u.uid,
                "email": u.email,
                "displayName": u.display_name,
                "photoUrl": u.photo_url,
                "disabled": u.disabled,
                "custom_claims": claims,
                "access_status": access_status
            })
        return users_list
    except Exception as e:
        logger.error(f"Error listing users: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/users/{uid}/role")
async def admin_update_role(
    uid: str,
    payload: UpdateRoleRequest,
    background_tasks: BackgroundTasks,
    admin_claims: dict = Depends(get_admin_user)
):
    """Updates the user's role claim (admin or user)."""
    if payload.role not in ["admin", "user"]:
        raise HTTPException(status_code=400, detail="Invalid role. Must be 'admin' or 'user'.")
    try:
        user = firebase_auth.get_user(uid)
        claims = user.custom_claims or {}
        claims["role"] = payload.role
        firebase_auth.set_custom_user_claims(uid, claims)

        name, email, photo_url = get_user_details(uid)
        if payload.role == "admin":
            background_tasks.add_task(admin_notifier.notify_new_admin_created, name, email, photo_url)

        gcp_logger.log_event(
            "User Role Updated",
            user_id=admin_claims.get("uid"),
            details={
                "admin_email": admin_claims.get("email"),
                "target_uid": uid,
                "target_email": email,
                "new_role": payload.role
            }
        )

        return {"success": True, "message": f"User role updated to {payload.role}."}
    except Exception as e:
        logger.error(f"Error updating role: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/users/{uid}/block")
async def admin_block_user(
    uid: str,
    background_tasks: BackgroundTasks,
    admin_claims: dict = Depends(get_admin_user)
):
    """Sets the 'blocked' claim to True."""
    try:
        user = firebase_auth.get_user(uid)
        claims = user.custom_claims or {}
        if claims.get("role") == "admin":
            raise HTTPException(status_code=400, detail="Admin users cannot be blocked.")

        claims["blocked"] = True
        firebase_auth.set_custom_user_claims(uid, claims)

        name, email, photo_url = get_user_details(uid)
        background_tasks.add_task(admin_notifier.notify_user_block_status, name, email, True, photo_url)

        gcp_logger.log_event(
            "User Blocked",
            user_id=admin_claims.get("uid"),
            details={
                "admin_email": admin_claims.get("email"),
                "target_uid": uid,
                "target_email": email
            }
        )

        return {"success": True, "message": "User blocked successfully."}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error blocking user: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/users/{uid}/unblock")
async def admin_unblock_user(
    uid: str,
    background_tasks: BackgroundTasks,
    admin_claims: dict = Depends(get_admin_user)
):
    """Sets the 'blocked' claim to False."""
    try:
        user = firebase_auth.get_user(uid)
        claims = user.custom_claims or {}
        claims["blocked"] = False
        firebase_auth.set_custom_user_claims(uid, claims)

        name, email, photo_url = get_user_details(uid)
        background_tasks.add_task(admin_notifier.notify_user_block_status, name, email, False, photo_url)

        gcp_logger.log_event(
            "User Unblocked",
            user_id=admin_claims.get("uid"),
            details={
                "admin_email": admin_claims.get("email"),
                "target_uid": uid,
                "target_email": email
            }
        )

        return {"success": True, "message": "User unblocked successfully."}
    except Exception as e:
        logger.error(f"Error unblocking user: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/requests")
async def admin_list_requests():
    """Lists pending and denied access requests from Firestore (excluding approved requests), enriched with user details."""
    if db is None:
        raise HTTPException(status_code=500, detail="Firestore is not available.")
    try:
        requests_ref = db.collection("access_requests").order_by("requested_at", direction=google_firestore.Query.DESCENDING)
        docs = requests_ref.stream()
        reqs = []
        for doc in docs:
            data = doc.to_dict()
            if data.get("status") == "approved":
                continue

            uid = data.get("uid")
            if uid:
                u_name, u_email, u_photo = get_user_details(uid)
                resolved_name = data.get("name") or data.get("displayName") or u_name
                if not resolved_name or resolved_name == "User":
                    resolved_name = u_email.split("@")[0] if u_email else "User"
                data["name"] = resolved_name
                data["displayName"] = resolved_name
                data["email"] = data.get("email") or u_email
                data["photoUrl"] = data.get("photoUrl") or u_photo

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


@router.post("/requests/{uid}/approve")
async def admin_approve_request(
    uid: str,
    background_tasks: BackgroundTasks,
    admin_claims: dict = Depends(get_admin_user)
):
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

        name, email, photo_url = get_user_details(uid)
        background_tasks.add_task(admin_notifier.notify_access_request_status, name, email, "approved", photo_url)

        gcp_logger.log_event(
            "Access Request Approved",
            user_id=admin_claims.get("uid"),
            details={
                "admin_email": admin_claims.get("email"),
                "target_uid": uid,
                "target_email": email
            }
        )

        return {"success": True, "message": "Access request approved successfully."}
    except Exception as e:
        logger.error(f"Error approving access request: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/requests/{uid}/deny")
async def admin_deny_request(
    uid: str,
    background_tasks: BackgroundTasks,
    admin_claims: dict = Depends(get_admin_user)
):
    """Denies an access request (updates Firestore to 'denied')."""
    try:
        if db is not None:
            db.collection("access_requests").document(uid).update({
                "status": "denied",
                "denied_at": google_firestore.SERVER_TIMESTAMP
            })

        name, email, photo_url = get_user_details(uid)
        background_tasks.add_task(admin_notifier.notify_access_request_status, name, email, "denied", photo_url)

        gcp_logger.log_event(
            "Access Request Denied",
            user_id=admin_claims.get("uid"),
            details={
                "admin_email": admin_claims.get("email"),
                "target_uid": uid,
                "target_email": email
            }
        )

        return {"success": True, "message": "Access request denied."}
    except Exception as e:
        logger.error(f"Error denying access request: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/jobs/{job_id}/stop")
async def admin_stop_job(
    job_id: str,
    background_tasks: BackgroundTasks,
    admin_claims: dict = Depends(get_admin_user)
):
    """Stops any running job."""
    job = manager.get_job(job_id)
    success = manager.stop_job(job_id)
    if success:
        owner_name, owner_email, _ = get_user_details(job.created_by if job else None)
        admin_name, admin_email, _ = get_user_details(admin_claims.get("uid"), admin_claims)
        background_tasks.add_task(
            admin_notifier.notify_job_admin_action,
            "stopped",
            job.id if job else job_id,
            job.movie_name if job else "N/A",
            owner_name,
            owner_email,
            job.service_provider if job else "N/A",
            job.theatres if job else [],
            job.date_str if job else "N/A",
            admin_name,
            admin_email
        )
        gcp_logger.log_event(
            "Admin Job Stopped",
            user_id=admin_claims.get("uid"),
            details={
                "admin_email": admin_email,
                "job_id": job_id,
                "movie_name": job.movie_name if job else "N/A",
                "owner_email": owner_email
            }
        )
        return {"success": True, "message": f"Job #{job_id} stopped."}
    else:
        raise HTTPException(status_code=404, detail=f"Job #{job_id} not found or could not be stopped.")


@router.delete("/jobs/{job_id}")
async def admin_delete_job(
    job_id: str,
    background_tasks: BackgroundTasks,
    admin_claims: dict = Depends(get_admin_user)
):
    """Deletes any job."""
    job = manager.get_job(job_id)
    success = manager.delete_job(job_id)
    if success:
        owner_name, owner_email, _ = get_user_details(job.created_by if job else None)
        admin_name, admin_email, _ = get_user_details(admin_claims.get("uid"), admin_claims)
        background_tasks.add_task(
            admin_notifier.notify_job_admin_action,
            "deleted",
            job.id if job else job_id,
            job.movie_name if job else "N/A",
            owner_name,
            owner_email,
            job.service_provider if job else "N/A",
            job.theatres if job else [],
            job.date_str if job else "N/A",
            admin_name,
            admin_email
        )
        gcp_logger.log_event(
            "Admin Job Deleted",
            user_id=admin_claims.get("uid"),
            details={
                "admin_email": admin_email,
                "job_id": job_id,
                "movie_name": job.movie_name if job else "N/A",
                "owner_email": owner_email
            }
        )
        return {"success": True, "message": f"Job #{job_id} deleted."}
    else:
        raise HTTPException(status_code=404, detail=f"Job #{job_id} not found.")
