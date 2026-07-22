# src/Backend/api/routers/auth.py

import logging
from fastapi import APIRouter, HTTPException, BackgroundTasks, Depends
from google.cloud import firestore as google_firestore

from lib.core.auth import get_current_user_claims, db
from lib.services.notification import admin_notifier
from lib.services.gcp_logger import gcp_logger
from api.schemas import RequestAccessPayload
from api.dependencies import get_user_details, verify_recaptcha

logger = logging.getLogger("ticketradar.api")

router = APIRouter(prefix="/api", tags=["Auth & Access"])


@router.post("/users/login-event")
async def record_login_event(
    background_tasks: BackgroundTasks,
    claims: dict = Depends(get_current_user_claims)
):
    """
    Records user login event and notifies admin on Discord if it's the user's first time logging in.
    """
    uid = claims.get("uid")
    if not uid:
        return {"success": False, "message": "Missing user UID in token claims."}

    user_name, email, photo_url = get_user_details(uid, claims)

    if db is not None:
        try:
            user_ref = db.collection("users").document(uid)
            doc = user_ref.get()
            is_first = not doc.exists or not doc.to_dict().get("first_login_notified", False)

            if is_first:
                user_ref.set({
                    "uid": uid,
                    "email": email,
                    "displayName": user_name,
                    "photoUrl": photo_url,
                    "first_login_notified": True,
                    "first_login_at": google_firestore.SERVER_TIMESTAMP
                }, merge=True)
                background_tasks.add_task(admin_notifier.notify_first_login, user_name, email, photo_url)

            gcp_logger.log_event(
                "User Logged In",
                user_id=uid,
                details={
                    "displayName": user_name,
                    "email": email,
                    "is_first_login": is_first
                }
            )
        except Exception as e:
            logger.error(f"Firestore check failed for user login {uid}: {e}")
            background_tasks.add_task(admin_notifier.notify_first_login, user_name, email, photo_url)
            gcp_logger.log_event(
                "User Logged In",
                user_id=uid,
                details={
                    "displayName": user_name,
                    "email": email,
                    "firestore_error": str(e)
                }
            )
    else:
        background_tasks.add_task(admin_notifier.notify_first_login, user_name, email, photo_url)
        gcp_logger.log_event(
            "User Logged In",
            user_id=uid,
            details={
                "displayName": user_name,
                "email": email
            }
        )

    return {"success": True}


@router.post("/request-access")
async def request_access(
    payload: RequestAccessPayload,
    background_tasks: BackgroundTasks,
    claims: dict = Depends(get_current_user_claims)
):
    """Submits a request access form to Firestore."""
    await verify_recaptcha(payload.recaptcha_token)

    if db is None:
        raise HTTPException(status_code=500, detail="Firestore is not configured.")

    uid = claims.get("uid")
    name, email_val, photo_url = get_user_details(uid, claims)

    # Check if already has a pending request
    doc_ref = db.collection("access_requests").document(uid)
    doc = doc_ref.get()
    if doc.exists:
        data = doc.to_dict()
        if data.get("status") == "pending":
            return {"success": True, "message": "Access request already pending."}

    doc_ref.set({
        "uid": uid,
        "email": email_val,
        "name": name,
        "displayName": name,
        "photoUrl": photo_url,
        "status": "pending",
        "requested_at": google_firestore.SERVER_TIMESTAMP
    })

    background_tasks.add_task(admin_notifier.notify_access_request_created, name, email_val, photo_url)

    gcp_logger.log_event(
        "Access Request Submitted",
        user_id=uid,
        details={
            "displayName": name,
            "email": email_val
        }
    )

    return {"success": True, "message": "Access request submitted successfully."}
