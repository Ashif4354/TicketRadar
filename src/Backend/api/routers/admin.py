import logging
import uuid
from fastapi import APIRouter, HTTPException, BackgroundTasks, Depends
from google.cloud import firestore as google_firestore

from lib.core.auth import get_admin_user, db, auth as firebase_auth
from lib.core.monitor import JobManager
from lib.services.notification import (
    admin_notifier,
    send_user_access_granted_email,
)
from lib.services.notification.user_mailer import send_admin_pricing_changed_email
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

