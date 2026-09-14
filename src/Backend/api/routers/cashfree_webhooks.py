# src/Backend/api/routers/cashfree_webhooks.py

import logging
from fastapi import APIRouter, Request, HTTPException
from google.cloud import firestore

from lib.core.auth import db
from lib.core.monitor import JobManager
from lib.core.job import MonitorJob
from lib.providers.payment.factory import PaymentGatewayFactory
from lib.services.wallet import WalletService

logger = logging.getLogger("ticketradar.api.cashfree_webhooks")
manager = JobManager()

router = APIRouter(prefix="/api/cashfree", tags=["Cashfree Webhooks"])

@router.post("/webhook")
async def handle_cashfree_webhook(request: Request):
    """
    Handles asynchronous webhook notifications from Cashfree Payment Gateway.
    Verifies cryptographic signature, guarantees idempotency, credits wallets,
    or finalizes two-step job creation.
    """
    raw_body = await request.body()
    headers = dict(request.headers)
    gateway = PaymentGatewayFactory.create()

    # 1. Signature Verification
    if not gateway.validate_webhook_signature(raw_body, headers):
        import os
        from lib.utils.config import settings
        disable_sec = os.getenv("DISABLE_SECURITY", "").lower() in ("true", "1") or (settings and getattr(settings, "disable_security", False))
        if not disable_sec:
            logger.warning("Cashfree webhook signature verification failed.")
            raise HTTPException(status_code=403, detail="Invalid Cashfree signature.")

    # 2. Parse standardized event
    try:
        event = gateway.parse_webhook_event(raw_body)
    except Exception as e:
        logger.error(f"Failed to parse Cashfree webhook event: {e}")
        raise HTTPException(status_code=400, detail=f"Unparseable webhook payload: {e}")

    order_id = event.order_id
    event_type = event.event_type
    refund_id = event.refund_id or ""

    if "REFUND" in event_type and refund_id:
        event_id = f"cf_{refund_id}_{event_type}"
    else:
        event_id = f"cf_{order_id}_{event_type}"

    # 3. Idempotency Gate
    if db:
        event_ref = db.collection("webhook_events").document(event_id)
        if event_ref.get().exists:
            logger.info(f"Cashfree event {event_id} already processed. Returning HTTP 200.")
            return {"status": "already_processed", "event_id": event_id}

        event_ref.set({
            "id": event_id,
            "source": "cashfree",
            "event_type": event_type,
            "raw_payload": event.raw,
            "signature_valid": True,
            "processed": False,
            "received_at": firestore.SERVER_TIMESTAMP,
        })

    # 4. Business Logic
    try:
        if event_type == "PAYMENT_SUCCESS_WEBHOOK":
            logger.info(f"Processing Cashfree PAYMENT_SUCCESS for order: {order_id}")
            payment_doc = None
            payment_data = {}

            if db:
                # Find payment by gateway_order_id
                docs = list(db.collection("payments").where("gateway_order_id", "==", order_id).limit(1).stream())
                if docs:
                    payment_doc = docs[0]
                    payment_data = payment_doc.to_dict() or {}

            if payment_data:
                uid = payment_data.get("uid")
                payment_type = payment_data.get("type")
                payment_id = payment_data.get("id")

                # Update payment document status
                if db and payment_doc:
                    payment_doc.reference.update({
                        "status": "success",
                        "gateway_payment_id": event.payment_id,
                        "completed_at": firestore.SERVER_TIMESTAMP,
                    })

                # A. Wallet Top-up
                if payment_type == "WALLET_TOPUP" and uid:
                    credit_key = f"topup_credit_{order_id}"
                    WalletService.credit(
                        uid=uid,
                        amount_paise=event.amount_paise or payment_data.get("amount_paise", 0),
                        txn_type="WALLET_TOPUP",
                        description=f"Wallet top-up via Cashfree (Payment #{event.payment_id or order_id})",
                        idempotency_key=credit_key,
                        payment_id=payment_id,
                    )
                    logger.info(f"Credited wallet for uid {uid} with ₹{(event.amount_paise or 0)/100:.2f}.")

                    # Send payment success email
                    recipient_email = payment_data.get("customer_email")
                    user_name = "User"
                    if db and uid:
                        try:
                            udoc = db.collection("users").document(uid).get()
                            if udoc.exists:
                                udata = udoc.to_dict() or {}
                                recipient_email = udata.get("email") or recipient_email
                                user_name = udata.get("displayName") or user_name
                        except Exception:
                            pass
                    if recipient_email:
                        from lib.services.notification.user_mailer import send_payment_success_email
                        import asyncio
                        try:
                            asyncio.create_task(send_payment_success_email(
                                recipient_email=recipient_email,
                                user_name=user_name,
                                order_id=order_id,
                                amount_inr=round((event.amount_paise or payment_data.get("amount_paise", 0)) / 100.0, 2),
                                payment_id=event.payment_id or "",
                                payment_type="Wallet Top-up"
                            ))
                        except Exception as pe_err:
                            logger.debug(f"Failed to dispatch payment success email: {pe_err}")

                # B. Two-step Job Creation Payment
                elif payment_type == "JOB_PAYMENT" and uid:
                    job_payload = payment_data.get("job_payload", {})
                    if job_payload:
                        new_job = MonitorJob(
                            params=job_payload.get("params", {}),
                            notification_medium=job_payload.get("notification_medium", "email"),
                            notification_config=job_payload.get("notification_config", {}),
                            service_provider=job_payload.get("service_provider", "bookmyshow"),
                            check_interval=job_payload.get("check_interval", 60),
                            created_by=uid,
                            phone_number=job_payload.get("phone_number"),
                            sms_consent=job_payload.get("sms_consent", False),
                            call_consent=job_payload.get("call_consent", False),
                            payment_method="cashfree",
                            payment_id=payment_id,
                            price_paise=payment_data.get("amount_paise", 0),
                            price_config_id=payment_data.get("price_config_id"),
                        )
                        started = manager.start_job(new_job)
                        if started:
                            logger.info(f"Two-step Cashfree job #{new_job.id} started successfully.")
                            if db and payment_doc:
                                payment_doc.reference.update({"job_id": new_job.id})

                            # Dispatch job created & payment success email
                            recipient_email = payment_data.get("customer_email")
                            user_name = "User"
                            if db and uid:
                                try:
                                    udoc = db.collection("users").document(uid).get()
                                    if udoc.exists:
                                        udata = udoc.to_dict() or {}
                                        recipient_email = udata.get("email") or recipient_email
                                        user_name = udata.get("displayName") or user_name
                                except Exception:
                                    pass
                            if recipient_email:
                                from lib.services.notification.user_mailer import send_payment_success_email, send_job_created_email
                                import asyncio
                                try:
                                    asyncio.create_task(send_payment_success_email(
                                        recipient_email=recipient_email,
                                        user_name=user_name,
                                        order_id=order_id,
                                        amount_inr=round(payment_data.get("amount_paise", 0) / 100.0, 2),
                                        payment_id=event.payment_id or "",
                                        payment_type="Ticket Monitor Job"
                                    ))
                                    asyncio.create_task(send_job_created_email(
                                        recipient_email=recipient_email,
                                        user_name=user_name,
                                        job_id=new_job.id,
                                        movie_name=new_job.movie_name,
                                        date_str=new_job.date_str,
                                        theatres=new_job.theatres,
                                        notification_medium=new_job.notification_medium,
                                        check_interval=new_job.check_interval
                                    ))
                                except Exception as je_err:
                                    logger.debug(f"Failed to dispatch job created email: {je_err}")
                        else:
                            # Orphan payment fallback: refund to wallet
                            logger.error(f"Failed to start job for payment {payment_id}. Issuing orphan refund to wallet.")
                            WalletService.credit(
                                uid=uid,
                                amount_paise=payment_data.get("amount_paise", 0),
                                txn_type="JOB_REFUND",
                                description=f"Refund for failed job creation #{payment_id}",
                                idempotency_key=f"orphan_refund_{payment_id}",
                                payment_id=payment_id,
                            )

        elif event_type == "PAYMENT_FAILED_WEBHOOK":
            logger.info(f"Cashfree PAYMENT_FAILED for order: {order_id}")
            payment_doc = None
            payment_data = {}
            if db:
                docs = list(db.collection("payments").where("gateway_order_id", "==", order_id).limit(1).stream())
                if docs:
                    payment_doc = docs[0]
                    payment_data = payment_doc.to_dict() or {}
                    payment_doc.reference.update({
                        "status": "failed",
                        "updated_at": firestore.SERVER_TIMESTAMP,
                    })

            # Send payment failed email
            if payment_data:
                uid = payment_data.get("uid")
                recipient_email = payment_data.get("customer_email")
                user_name = "User"
                if db and uid:
                    try:
                        udoc = db.collection("users").document(uid).get()
                        if udoc.exists:
                            udata = udoc.to_dict() or {}
                            recipient_email = udata.get("email") or recipient_email
                            user_name = udata.get("displayName") or user_name
                    except Exception:
                        pass
                if recipient_email:
                    from lib.services.notification.user_mailer import send_payment_failed_email, send_wallet_topup_failed_email
                    import asyncio
                    amount_inr = round(payment_data.get("amount_paise", 0) / 100.0, 2)
                    ptype = payment_data.get("type")
                    try:
                        if ptype == "WALLET_TOPUP":
                            asyncio.create_task(send_wallet_topup_failed_email(
                                recipient_email=recipient_email,
                                user_name=user_name,
                                amount_inr=amount_inr,
                                order_id=order_id,
                                reason="Payment was declined or cancelled at checkout."
                            ))
                        asyncio.create_task(send_payment_failed_email(
                            recipient_email=recipient_email,
                            user_name=user_name,
                            order_id=order_id,
                            amount_inr=amount_inr,
                            failure_reason="Payment was declined or cancelled at checkout."
                        ))
                    except Exception as fe_err:
                        logger.debug(f"Failed to dispatch payment failed email: {fe_err}")

        # Mark event as processed
        if db:
            db.collection("webhook_events").document(event_id).update({
                "processed": True,
                "processed_at": firestore.SERVER_TIMESTAMP,
            })

    except Exception as e:
        logger.error(f"Error executing Cashfree webhook business logic: {e}")
        if db:
            db.collection("webhook_events").document(event_id).update({
                "processing_error": str(e),
            })
        raise HTTPException(status_code=500, detail="Error processing webhook.")

    return {"status": "ok", "event_id": event_id}
