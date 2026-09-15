import logging
import uuid
import html
from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException, BackgroundTasks, Depends, Query, Response
from fastapi.responses import HTMLResponse
from google.cloud import firestore as google_firestore

from lib.core.auth import get_admin_user, db, auth as firebase_auth
from lib.core.monitor import JobManager
from lib.services.notification import (
    admin_notifier,
    send_user_access_granted_email,
)
from lib.services.notification.user_mailer import send_admin_pricing_changed_email
from lib.services.notification.templates.email import EmailTemplates
from lib.services.gcp_logger import gcp_logger
from lib.services.pricing import PricingService
from lib.services.wallet import WalletService
from lib.providers.payment.factory import PaymentGatewayFactory
from api.schemas import (
    UpdateRoleRequest,
    UpdatePricesRequest,
    AdminAdjustWalletRequest,
    AdminGatewayRefundRequest,
    AdminCashfreeRefundRequest,
)
from api.dependencies import get_user_details, require_payments_enabled

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
    """Unblocks a user by clearing the user's blocked status.
    
    Parameters:
        uid (str): The Firebase user ID to unblock.
        background_tasks (BackgroundTasks): Background task manager for the unblock notification.
        admin_claims (dict): Claims for the administrator performing the action.
    
    Returns:
        dict: A success response with a confirmation message.
    """
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
    """
    List access requests that have not been approved, enriched with user details and ISO-formatted timestamps.
    
    Returns:
    	list[dict]: Access request records excluding approved requests.
    """
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
        background_tasks.add_task(send_user_access_granted_email, email, name)

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


@router.post("/jobs/{job_id}/start")
async def admin_start_job(
    job_id: str,
    background_tasks: BackgroundTasks,
    admin_claims: dict = Depends(get_admin_user)
):
    """Starts or restarts any stopped or non-started job without charging the user."""
    job = manager.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail=f"Job #{job_id} not found.")

    if job.status == "Running":
        return {"success": True, "message": f"Job #{job_id} is already running.", "state": job.get_state()}

    job.update_state("Idle", "Started by administrator (Free).")
    success = manager.start_job(job)
    if success:
        owner_name, owner_email, _ = get_user_details(job.created_by if job else None)
        admin_name, admin_email, _ = get_user_details(admin_claims.get("uid"), admin_claims)
        background_tasks.add_task(
            admin_notifier.notify_job_admin_action,
            "started",
            job.id,
            job.movie_name,
            owner_name,
            owner_email,
            job.service_provider,
            job.theatres,
            job.date_str,
            admin_name,
            admin_email
        )
        gcp_logger.log_event(
            "Admin Job Started",
            user_id=admin_claims.get("uid"),
            details={
                "admin_email": admin_email,
                "job_id": job_id,
                "movie_name": job.movie_name,
                "owner_email": owner_email,
                "charged": False
            }
        )
        return {"success": True, "message": f"Job #{job_id} started by admin (free of charge).", "state": job.get_state()}
    else:
        raise HTTPException(status_code=500, detail=f"Failed to start job #{job_id}.")


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


@router.get("/pricing", dependencies=[Depends(require_payments_enabled)])
async def admin_get_pricing():
    """Returns current active prices and price update history."""
    current = PricingService.get_current_prices()
    history = PricingService.get_price_history(limit=25)
    return {
        "current": current,
        "history": history,
    }


@router.post("/pricing", dependencies=[Depends(require_payments_enabled)])
async def admin_update_pricing(
    payload: UpdatePricesRequest,
    background_tasks: BackgroundTasks,
    admin_claims: dict = Depends(get_admin_user)
):
    """Updates notification pricing with mandatory reason, creating audit logs."""
    try:
        old_prices = PricingService.get_current_prices()
        new_config = PricingService.update_prices(
            admin_uid=admin_claims.get("uid"),
            admin_email=admin_claims.get("email", ""),
            sms_paise=payload.sms_paise,
            whatsapp_paise=payload.whatsapp_paise,
            phone_call_paise=payload.phone_call_paise,
            note=payload.note,
            email_paise=payload.email_paise,
            discord_paise=payload.discord_paise,
        )
        admin_email = admin_claims.get("email", "")
        admin_name = admin_claims.get("name") or admin_claims.get("displayName") or "Admin"
        if admin_email:
            background_tasks.add_task(
                send_admin_pricing_changed_email,
                admin_email,
                admin_name,
                old_prices,
                new_config,
                payload.note
            )
        gcp_logger.log_event(
            "Pricing Updated",
            user_id=admin_claims.get("uid"),
            details={
                "admin_email": admin_email,
                "sms_paise": payload.sms_paise,
                "whatsapp_paise": payload.whatsapp_paise,
                "phone_call_paise": payload.phone_call_paise,
                "email_paise": payload.email_paise,
                "discord_paise": payload.discord_paise,
                "note": payload.note
            }
        )
        return {"success": True, "config": new_config}
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        logger.error(f"Error updating prices: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/transactions", dependencies=[Depends(require_payments_enabled)])
async def admin_get_all_transactions(
    page: int = 1,
    page_size: int = 20,
    uid: str | None = None,
    txn_type: str | None = None,
    direction: str | None = None,
    search: str | None = None,
    admin_claims: dict = Depends(get_admin_user)
):
    """Retrieves all transactions of all users, paginated, with filters."""
    return WalletService.get_all_transactions(
        page=page,
        page_size=page_size,
        uid=uid,
        txn_type=txn_type,
        direction=direction,
        search=search,
    )


@router.get("/wallets/{uid}", dependencies=[Depends(require_payments_enabled)])
async def admin_get_user_wallet(uid: str):
    """Retrieves user wallet balance and transaction ledger."""
    balance_paise = WalletService.get_balance(uid)
    txns = WalletService.get_transactions(uid, limit=50)
    return {
        "uid": uid,
        "balance_paise": balance_paise,
        "balance_inr": round(balance_paise / 100.0, 2),
        "transactions": txns,
    }


@router.post("/wallets/{uid}/adjust", dependencies=[Depends(require_payments_enabled)])
async def admin_adjust_wallet(
    uid: str,
    payload: AdminAdjustWalletRequest,
    admin_claims: dict = Depends(get_admin_user)
):
    """
    Credits or debits a user's wallet with mandatory audit explanation.
    Creates an immutable wallet transaction record and an admin audit log entry.
    """
    direction = payload.direction.upper()
    amount_paise = payload.amount_paise
    reason = payload.reason
    admin_uid = admin_claims.get("uid")
    admin_email = admin_claims.get("email", "")

    idempotency_key = f"admin_adj_{uuid.uuid4()}"
    txn_type = "ADMIN_CREDIT" if direction == "CREDIT" else "ADMIN_DEBIT"

    try:
        if direction == "CREDIT":
            txn = WalletService.credit(
                uid=uid,
                amount_paise=amount_paise,
                txn_type=txn_type,
                description=f"Admin credit: {reason}",
                idempotency_key=idempotency_key,
                created_by=f"admin:{admin_uid}",
            )
        else:
            txn = WalletService.debit(
                uid=uid,
                amount_paise=amount_paise,
                txn_type=txn_type,
                description=f"Admin debit: {reason}",
                idempotency_key=idempotency_key,
                created_by=f"admin:{admin_uid}",
            )

        # Audit log
        if db:
            log_id = str(uuid.uuid4())
            db.collection("admin_audit_logs").document(log_id).set({
                "id": log_id,
                "admin_uid": admin_uid,
                "admin_email": admin_email,
                "action_type": txn_type,
                "target_uid": uid,
                "amount_paise": amount_paise,
                "reason": reason,
                "new_value": txn,
                "created_at": google_firestore.SERVER_TIMESTAMP,
            })

        gcp_logger.log_event(
            "Admin Wallet Adjusted",
            user_id=admin_uid,
            details={
                "admin_email": admin_email,
                "target_uid": uid,
                "direction": direction,
                "amount_paise": amount_paise,
                "amount_inr": round(amount_paise / 100.0, 2),
                "reason": reason,
                "txn_id": txn.get("id") if isinstance(txn, dict) else None,
            }
        )

        return {"success": True, "transaction": txn}
    except Exception as e:
        logger.error(f"Admin wallet adjustment failed for {uid}: {e}")
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/refunds/gateway", dependencies=[Depends(require_payments_enabled)])
@router.post("/refunds/cashfree", dependencies=[Depends(require_payments_enabled)])
async def admin_gateway_refund(
    payload: AdminGatewayRefundRequest,
    admin_claims: dict = Depends(get_admin_user)
):
    """
    Initiates an admin-directed refund back to the user's original payment method via the configured gateway.
    Requires an existing gateway order ID.
    """
    admin_uid = admin_claims.get("uid")
    admin_email = admin_claims.get("email", "")
    refund_id = f"ref_{str(uuid.uuid4())[:8]}"

    try:
        gateway = PaymentGatewayFactory.create()
        result = await gateway.create_refund(
            order_id=payload.order_id,
            amount_paise=payload.amount_paise,
            refund_id=refund_id,
            reason=payload.reason,
        )

        if not result.success:
            raise HTTPException(status_code=400, detail=result.error_message or "Payment gateway refund failed.")

        # Record refund doc in refunds collection
        if db:
            ref_id = str(uuid.uuid4())
            db.collection("refunds").document(ref_id).set({
                "id": ref_id,
                "order_id": payload.order_id,
                "gateway_refund_id": result.provider_refund_id,
                "type": "GATEWAY_REFUND",
                "amount_paise": payload.amount_paise,
                "status": "success",
                "destination": "original_payment_method",
                "reason": payload.reason,
                "job_id": payload.job_id,
                "initiated_by": f"admin:{admin_uid}",
                "idempotency_key": refund_id,
                "created_at": google_firestore.SERVER_TIMESTAMP,
            })

            # Record audit log
            log_id = str(uuid.uuid4())
            db.collection("admin_audit_logs").document(log_id).set({
                "id": log_id,
                "admin_uid": admin_uid,
                "admin_email": admin_email,
                "action_type": "GATEWAY_REFUND_INITIATED",
                "amount_paise": payload.amount_paise,
                "reason": payload.reason,
                "metadata": {
                    "order_id": payload.order_id,
                    "refund_id": refund_id,
                    "gateway_refund_id": result.provider_refund_id,
                    "cf_refund_id": result.provider_refund_id,
                },
                "created_at": google_firestore.SERVER_TIMESTAMP,
            })

        gcp_logger.log_event(
            "Admin Gateway Refund Initiated",
            user_id=admin_uid,
            details={
                "admin_email": admin_email,
                "order_id": payload.order_id,
                "refund_id": refund_id,
                "gateway_refund_id": result.provider_refund_id,
                "amount_paise": payload.amount_paise,
                "amount_inr": round(payload.amount_paise / 100.0, 2),
                "reason": payload.reason,
                "job_id": payload.job_id,
            }
        )

        return {
            "success": True,
            "refund_id": refund_id,
            "provider_refund_id": result.provider_refund_id,
            "message": "Refund to original payment method initiated successfully."
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error processing payment gateway refund: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/audit-logs")
async def admin_get_audit_logs(limit: int = 50):
    """Retrieves immutable audit logs of administrative and financial actions."""
    if not db:
        return []
    try:
        docs = (
            db.collection("admin_audit_logs")
            .order_by("created_at", direction=google_firestore.Query.DESCENDING)
            .limit(limit)
            .stream()
        )
        logs = []
        for doc in docs:
            item = doc.to_dict() or {}
            if "created_at" in item and item["created_at"]:
                try:
                    item["created_at"] = item["created_at"].isoformat()
                except Exception:
                    pass
            logs.append(item)
        return logs
    except Exception as e:
        logger.error(f"Error fetching audit logs: {e}")
        # Fallback without composite index requirement
        try:
            docs = list(db.collection("admin_audit_logs").stream())
            items = [d.to_dict() or {} for d in docs]
            items.sort(key=lambda x: str(x.get("created_at", "")), reverse=True)
            for item in items[:limit]:
                if "created_at" in item and item["created_at"]:
                    try:
                        item["created_at"] = item["created_at"].isoformat()
                    except Exception:
                        pass
            return items[:limit]
        except Exception:
            return []


def _build_all_receipts():
    """Gathers and standardizes financial transactions into receipts enriched with customer metadata."""
    user_map = {}
    if firebase_auth:
        try:
            page = firebase_auth.list_users()
            if hasattr(page, "users"):
                for u in page.users:
                    u_email = getattr(u, "email", "") or ""
                    u_name = getattr(u, "display_name", None) or (u_email.split("@")[0] if u_email else "User")
                    u_phone = getattr(u, "phone_number", "") or ""
                    user_map[u.uid] = {
                        "user_name": u_name,
                        "email": u_email,
                        "phone": u_phone,
                    }
        except Exception as e:
            logger.debug(f"Could not list users from firebase_auth: {e}")

    if db is not None:
        try:
            req_docs = db.collection("access_requests").stream()
            for rd in req_docs:
                rdata = rd.to_dict() or {}
                ruid = rdata.get("uid") or rd.id
                if ruid not in user_map:
                    user_map[ruid] = {
                        "user_name": rdata.get("name") or rdata.get("user_name") or "User",
                        "email": rdata.get("email") or "",
                        "phone": rdata.get("phone") or rdata.get("phone_number") or "",
                    }
                else:
                    if not user_map[ruid].get("phone") and (rdata.get("phone") or rdata.get("phone_number")):
                        user_map[ruid]["phone"] = rdata.get("phone") or rdata.get("phone_number")
        except Exception as fe:
            logger.debug(f"Could not fetch access_requests for user map: {fe}")

    receipts_list = []
    seen_payment_ids = set()

    if db is not None:
        try:
            tx_docs = db.collection("wallet_transactions").stream()
            for doc in tx_docs:
                data = doc.to_dict() or {}
                t_id = doc.id
                u_id = data.get("uid", "")
                uinfo = user_map.get(u_id, {})
                amt_paise = int(data.get("amount_paise", 0))
                bal_paise = int(data.get("balance_paise", 0))
                amt_inr = round(amt_paise / 100.0, 2)
                bal_inr = round(bal_paise / 100.0, 2)
                ttype = str(data.get("type", "TRANSACTION")).upper()
                dirn = str(data.get("direction", "CREDIT")).upper()

                created_at = data.get("created_at")
                if hasattr(created_at, "isoformat"):
                    created_at_iso = created_at.isoformat()
                else:
                    created_at_iso = str(created_at or "")

                date_compact = created_at_iso[:10].replace("-", "") if created_at_iso else "20260914"
                short_hash = f"{abs(hash(t_id)) % 100000:05d}"
                rec_id = data.get("receipt_id") or f"REC-TR-{date_compact}-{short_hash}"

                pay_ref = data.get("payment_id") or data.get("refund_id") or ""
                ord_ref = data.get("idempotency_key") or data.get("job_id") or pay_ref or t_id
                if pay_ref:
                    seen_payment_ids.add(pay_ref)
                if data.get("idempotency_key"):
                    seen_payment_ids.add(data.get("idempotency_key"))

                method = data.get("payment_method")
                if not method:
                    if ttype in ("TOPUP", "WALLET_TOPUP"):
                        method = "UPI / Gateway"
                    elif ttype == "REFUND":
                        method = "Wallet Balance Credit"
                    elif dirn == "DEBIT":
                        method = "TicketRadar Wallet"
                    else:
                        method = "Online Payment"

                prev_bal_inr = round(max(0, bal_paise - amt_paise) / 100.0, 2) if dirn == "CREDIT" else round((bal_paise + amt_paise) / 100.0, 2)

                receipts_list.append({
                    "receipt_id": rec_id,
                    "id": t_id,
                    "uid": u_id,
                    "user_name": uinfo.get("user_name") or "Valued Customer",
                    "email": uinfo.get("email") or "",
                    "phone": uinfo.get("phone") or "",
                    "type": ttype,
                    "direction": dirn,
                    "status": "SUCCESS",
                    "amount_paise": amt_paise,
                    "amount_inr": amt_inr,
                    "balance_inr": bal_inr,
                    "prev_balance_inr": prev_bal_inr,
                    "order_id": ord_ref,
                    "job_id": data.get("job_id") or "",
                    "payment_id": pay_ref,
                    "payment_method": method,
                    "description": data.get("description") or f"TicketRadar {ttype.replace('_', ' ').title()}",
                    "created_at": created_at_iso,
                    "source": "wallet_transactions",
                })
        except Exception as e:
            logger.error(f"Error reading wallet_transactions for receipts: {e}")

        try:
            pay_docs = db.collection("payments").stream()
            for doc in pay_docs:
                data = doc.to_dict() or {}
                p_id = doc.id
                gw_order = data.get("gateway_order_id") or data.get("idempotency_key") or ""
                gw_pay = data.get("gateway_payment_id") or ""
                if p_id in seen_payment_ids or (gw_order and gw_order in seen_payment_ids) or (gw_pay and gw_pay in seen_payment_ids):
                    continue

                status = str(data.get("status", "")).upper()
                # Include completed payments and failed transaction notices (excluding pending/abandoned checkouts)
                if status not in ("SUCCESS", "PAID", "FAILED"):
                    continue

                u_id = data.get("uid", "")
                uinfo = user_map.get(u_id, {})
                amt_paise = int(data.get("amount_paise", 0))
                amt_inr = round(amt_paise / 100.0, 2)
                ttype = str(data.get("type", "PAYMENT")).upper()

                created_at = data.get("created_at") or data.get("completed_at")
                if hasattr(created_at, "isoformat"):
                    created_at_iso = created_at.isoformat()
                else:
                    created_at_iso = str(created_at or "")

                date_compact = created_at_iso[:10].replace("-", "") if created_at_iso else "20260914"
                short_hash = f"{abs(hash(p_id)) % 100000:05d}"
                rec_id = data.get("receipt_id") or f"REC-TR-{date_compact}-{short_hash}"

                gw_name = (data.get("gateway_name") or "Cashfree").capitalize()
                method = data.get("payment_method") or f"{gw_name} PG"

                receipts_list.append({
                    "receipt_id": rec_id,
                    "id": p_id,
                    "uid": u_id,
                    "user_name": uinfo.get("user_name") or "Valued Customer",
                    "email": uinfo.get("email") or "",
                    "phone": uinfo.get("phone") or "",
                    "type": ttype,
                    "direction": "CREDIT" if ttype in ("TOPUP", "WALLET_TOPUP") else "DEBIT",
                    "status": status,
                    "amount_paise": amt_paise,
                    "amount_inr": amt_inr,
                    "balance_inr": None,
                    "prev_balance_inr": None,
                    "order_id": gw_order or p_id,
                    "job_id": data.get("job_id") or "",
                    "payment_id": gw_pay or p_id,
                    "payment_method": method,
                    "description": f"TicketRadar {ttype.replace('_', ' ').title()}",
                    "created_at": created_at_iso,
                    "source": "payments",
                })
        except Exception as e:
            logger.error(f"Error reading payments collection for receipts: {e}")

    return receipts_list


@router.get("/receipts", dependencies=[Depends(require_payments_enabled)])
async def admin_get_receipts(
    page: int = 1,
    page_size: int = 20,
    search: str | None = None,
    receipt_id: str | None = None,
    uid: str | None = None,
    email: str | None = None,
    phone: str | None = None,
    order_id: str | None = None,
    payment_id: str | None = None,
    payment_method: str | None = None,
    receipt_type: str | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
    admin_claims: dict = Depends(get_admin_user),
):
    """Retrieves paginated, searchable receipts filtered by any metadata."""
    all_receipts = _build_all_receipts()
    filtered = []

    for r in all_receipts:
        if search and search.strip():
            s = search.strip().lower()
            searchable_fields = [
                r.get("receipt_id", ""),
                r.get("uid", ""),
                r.get("user_name", ""),
                r.get("email", ""),
                r.get("phone", ""),
                r.get("order_id", ""),
                r.get("job_id", ""),
                r.get("payment_id", ""),
                r.get("payment_method", ""),
                r.get("type", ""),
                r.get("status", ""),
                r.get("description", ""),
                f"₹{r.get('amount_inr', 0)}",
                str(r.get("amount_inr", "")),
            ]
            if not any(s in str(f).lower() for f in searchable_fields if f):
                continue

        if receipt_id and receipt_id.strip():
            if receipt_id.strip().lower() not in r.get("receipt_id", "").lower():
                continue

        if uid and uid.strip():
            if uid.strip().lower() != r.get("uid", "").lower():
                continue

        if email and email.strip():
            if email.strip().lower() not in r.get("email", "").lower():
                continue

        if phone and phone.strip():
            p_clean = phone.strip().replace(" ", "").replace("-", "")
            r_phone = r.get("phone", "").replace(" ", "").replace("-", "")
            if p_clean not in r_phone:
                continue

        if order_id and order_id.strip():
            oid = order_id.strip().lower()
            if oid not in r.get("order_id", "").lower() and oid not in r.get("job_id", "").lower():
                continue

        if payment_id and payment_id.strip():
            pid = payment_id.strip().lower()
            if pid not in r.get("payment_id", "").lower():
                continue

        if payment_method and payment_method.strip():
            pm = payment_method.strip().lower()
            if pm != "all" and pm not in r.get("payment_method", "").lower():
                continue

        if receipt_type and receipt_type.strip():
            rt = receipt_type.strip().upper()
            if rt != "ALL" and rt not in r.get("type", "").upper():
                continue

        c_at = r.get("created_at", "")
        if start_date and start_date.strip():
            if c_at and c_at[:10] < start_date.strip()[:10]:
                continue
        if end_date and end_date.strip():
            if c_at and c_at[:10] > end_date.strip()[:10]:
                continue

        filtered.append(r)

    filtered.sort(key=lambda x: str(x.get("created_at", "")), reverse=True)

    total = len(filtered)
    total_pages = (total + page_size - 1) // page_size if page_size > 0 else 1
    start = (max(1, page) - 1) * page_size
    end = start + page_size
    paged_items = filtered[start:end]

    return {
        "items": paged_items,
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": total_pages,
    }


@router.get("/receipts/{receipt_id}/render", dependencies=[Depends(require_payments_enabled)])
async def admin_render_receipt(
    receipt_id: str,
    format: str | None = None,
    admin_claims: dict = Depends(get_admin_user),
):
    """Dynamically generates and returns the HTML receipt for the specified receipt ID or transaction ID."""
    all_receipts = _build_all_receipts()
    target = None
    target_id_clean = receipt_id.strip().lower()
    for r in all_receipts:
        if (
            r.get("receipt_id", "").lower() == target_id_clean
            or r.get("id", "").lower() == target_id_clean
            or r.get("order_id", "").lower() == target_id_clean
            or r.get("payment_id", "").lower() == target_id_clean
        ):
            target = r
            break

    if not target:
        raise HTTPException(status_code=404, detail=f"Receipt '{receipt_id}' not found.")

    rec_type = target.get("type", "PAYMENT").upper()
    amt_inr = target.get("amount_inr", 0.0)
    direction = target.get("direction", "CREDIT").upper()
    status = target.get("status", "SUCCESS").upper()

    date_raw = target.get("created_at", "")
    date_display = date_raw
    if date_raw:
        try:
            clean_iso = date_raw.replace("Z", "+00:00")
            dt = datetime.fromisoformat(clean_iso)
            date_display = dt.strftime("%d %b %Y, %I:%M %p UTC")
        except Exception:
            date_display = date_raw

    items = [
        {
            "desc": f"<strong>{html.escape(target.get('description') or 'TicketRadar Service')}</strong><br><span style='color: #64748b; font-size: 11px;'>Reference: {html.escape(target.get('order_id') or target.get('payment_id') or 'N/A')}</span>",
            "qty": "1",
            "rate": f"₹{amt_inr:.2f}",
            "amount": f"₹{amt_inr:.2f}",
        }
    ]

    wallet_ledger = None
    if target.get("balance_inr") is not None:
        prev_b = target.get("prev_balance_inr", 0.0)
        new_b = target.get("balance_inr", 0.0)
        is_credit = direction == "CREDIT"
        sign = "+" if is_credit else "-"
        color = "#059669" if is_credit else "#f87171"
        wallet_ledger = {
            "prev_bal": f"₹{prev_b:.2f}",
            "action_label": "Amount Credited:" if is_credit else "Amount Debited:",
            "impact_amt": f"{sign}₹{amt_inr:.2f}",
            "impact_color": color,
            "new_bal": f"₹{new_b:.2f}",
        }

    alert_banner = None
    terms_notes = None

    if status == "FAILED":
        doc_title = "PAYMENT FAILED NOTICE"
        status_label = "● PAYMENT FAILED"
        st_color, st_bg, st_border = "#dc2626", "#fef2f2", "#fecaca"
        accent_grad = "linear-gradient(90deg, #ef4444, #f97316)"
        total_label = "Attempted Amount"
        grand_total_color = "#dc2626"
        alert_banner = f"""
        <div style="margin: 0 0 24px 0; padding: 16px 18px; background-color: #fff7ed; border: 1px solid #fdba74; border-left: 5px solid #ea580c; border-radius: 8px;">
          <div style="font-size: 13px; font-weight: 700; color: #9a3412; margin-bottom: 6px;">
            ⚠️ Was money deducted from the customer's bank account?
          </div>
          <p style="margin: 0; font-size: 12px; color: #7c2d12; line-height: 1.6;">
            If any amount was debited from the customer's bank account, card, or UPI wallet during this attempt, <strong>please do not worry</strong>. The transaction was not completed on TicketRadar, and <strong>the debited money will be automatically refunded by their bank to their original payment method within 3 to 5 business days</strong>.
          </p>
          <p style="margin: 6px 0 0 0; font-size: 11px; color: #9a3412;">
            Order ID: <strong>#{html.escape(target.get('order_id') or 'N/A')}</strong> • Support: <a href="mailto:darkglance.developer@gmail.com" style="color: #ea580c; font-weight: 600; text-decoration: underline;">darkglance.developer@gmail.com</a>
          </p>
        </div>
        """
        terms_notes = [
            "This document confirms an unsuccessful transaction attempt on TicketRadar.",
            "TicketRadar has not captured or claimed these funds.",
            "Any debited money is held in the banking system and will reverse automatically within 3-5 business days.",
            "The customer may safely re-attempt this transaction from their TicketRadar dashboard."
        ]
    elif rec_type == "REFUND":
        doc_title = "REFUND RECEIPT"
        status_label = "● REFUNDED"
        st_color, st_bg, st_border = "#2563eb", "#eff6ff", "#bfdbfe"
        accent_grad = "linear-gradient(90deg, #f59e0b, #ef4444)"
        total_label = "Net Refunded"
        grand_total_color = "#d97706"
    else:
        doc_title = "PAYMENT RECEIPT"
        status_label = "● PAID"
        st_color, st_bg, st_border = "#059669", "#ecfdf5", "#a7f3d0"
        accent_grad = "linear-gradient(90deg, #10b981, #06b6d4)"
        total_label = "Total Paid"
        grand_total_color = "#0f172a"

    html_content = EmailTemplates._render_invoice_html(
        doc_title=doc_title,
        status_label=status_label,
        status_color=st_color,
        status_bg=st_bg,
        status_border=st_border,
        accent_gradient=accent_grad,
        invoice_id=target.get("receipt_id", ""),
        order_id=target.get("order_id", "N/A"),
        payment_id=target.get("payment_id", "N/A"),
        payment_method=target.get("payment_method", "Online Payment"),
        customer_name=target.get("user_name", "Valued Customer"),
        customer_email=target.get("email", ""),
        customer_phone=target.get("phone", ""),
        customer_id=target.get("uid", ""),
        issue_date=date_display,
        items=items,
        subtotal_str=f"₹{amt_inr:.2f}",
        tax_str=None,
        tax_label="",
        total_label=total_label,
        grand_total_str=f"₹{amt_inr:.2f}",
        grand_total_color=grand_total_color,
        wallet_ledger=wallet_ledger,
        terms_notes=terms_notes,
        alert_banner_html=alert_banner,
    )

    if format == "html":
        return HTMLResponse(content=html_content)

    return {
        "html": html_content,
        "receipt": target,
    }

