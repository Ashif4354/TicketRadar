# src/Backend/api/routers/payments.py

import logging
import uuid
from fastapi import APIRouter, HTTPException, Depends
from google.cloud import firestore

from lib.core.auth import get_authorized_user, db
from lib.utils.config import settings
from lib.services.pricing import PricingService
from lib.providers.payment.factory import PaymentGatewayFactory
from api.dependencies import require_payments_enabled, get_user_details, require_terms_accepted
from api.schemas import CreateJobRequest

logger = logging.getLogger("ticketradar.api.payments")

router = APIRouter(prefix="/api/payments", tags=["Payments"])

@router.get("/prices")
async def get_prices():
    """Returns current active notification pricing in paise and INR."""
    prices = PricingService.get_current_prices()
    return {
        "config_id": prices.get("id"),
        "sms_paise": prices.get("sms_paise", 50),
        "whatsapp_paise": prices.get("whatsapp_paise", 100),
        "phone_call_paise": prices.get("phone_call_paise", 150),
        "email_paise": prices.get("email_paise", 0),
        "discord_paise": prices.get("discord_paise", 0),
        "sms_inr": round(prices.get("sms_paise", 50) / 100.0, 2),
        "whatsapp_inr": round(prices.get("whatsapp_paise", 100) / 100.0, 2),
        "phone_call_inr": round(prices.get("phone_call_paise", 150) / 100.0, 2),
        "email_inr": round(prices.get("email_paise", 0) / 100.0, 2),
        "discord_inr": round(prices.get("discord_paise", 0) / 100.0, 2),
    }

@router.post("/job/initiate", dependencies=[Depends(require_payments_enabled)])
async def initiate_job_payment(
    payload: CreateJobRequest,
    claims: dict = Depends(get_authorized_user)
):
    """
    Step 1 of Cashfree Two-Step Job Creation:
    Generates a Cashfree order session for creating and paying for a job.
    Upon payment success, Cashfree webhook will finalize and start the monitor job.
    """
    await require_terms_accepted(claims)
    uid = claims.get("uid")
    _, email, _ = get_user_details(uid, claims)

    price_paise, config_id = PricingService.get_price_for_medium(payload.notification_medium)
    if price_paise <= 0:
        raise HTTPException(
            status_code=400,
            detail=f"Notification medium {payload.notification_medium} is free of charge. No payment required."
        )

    payment_id = str(uuid.uuid4())
    idempotency_key = f"job_pay_{payment_id}"

    # Store pending payment with embedded job request parameters
    if db:
        try:
            active_gw = (settings.payment_gateway if settings else "cashfree").strip().lower()
            job_payload_dict = payload.model_dump() if hasattr(payload, "model_dump") else payload.dict()
            db.collection("payments").document(payment_id).set({
                "id": payment_id,
                "uid": uid,
                "type": "JOB_PAYMENT",
                "amount_paise": price_paise,
                "price_config_id": config_id,
                "status": "pending",
                "payment_method": payload.payment_method or "gateway",
                "gateway_name": active_gw,
                "gateway_order_id": idempotency_key,
                "idempotency_key": idempotency_key,
                "job_payload": job_payload_dict,
                "created_at": firestore.SERVER_TIMESTAMP,
            })
        except Exception as e:
            logger.error(f"Failed to record pending job payment doc: {e}")

    try:
        gateway = PaymentGatewayFactory.create()
        order_res = await gateway.create_order(
            amount_paise=price_paise,
            idempotency_key=idempotency_key,
            customer_uid=uid,
            customer_email=email or "user@ticketradar.local",
            metadata={
                "type": "JOB_PAYMENT",
                "payment_id": payment_id,
                "customer_phone": payload.phone_number or "9999999999",
            }
        )

        if db:
            db.collection("payments").document(payment_id).update({
                "gateway_session_id": order_res.session_token,
                "checkout_url": order_res.checkout_url,
            })

        return {
            "payment_id": payment_id,
            "order_id": order_res.order_id,
            "session_token": order_res.session_token,
            "checkout_url": order_res.checkout_url,
            "amount_paise": price_paise,
            "amount_inr": round(price_paise / 100.0, 2),
        }
    except Exception as e:
        logger.error(f"Error creating payment order for job: {e}")
        if db:
            db.collection("payments").document(payment_id).update({"status": "failed"})
        raise HTTPException(status_code=500, detail=f"Failed to create payment order: {str(e)}")

@router.get("/{payment_id}/status")
async def get_payment_status(
    payment_id: str,
    claims: dict = Depends(get_authorized_user)
):
    """
    Polls the status of a payment by payment_id.
    Used by the frontend to detect when a Cashfree webhook has finalized job creation.
    """
    uid = claims.get("uid")
    if not db:
        raise HTTPException(status_code=500, detail="Database connection unavailable.")

    doc = db.collection("payments").document(payment_id).get()
    if not doc.exists:
        raise HTTPException(status_code=404, detail="Payment record not found.")

    data = doc.to_dict() or {}
    if data.get("uid") != uid and claims.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Forbidden access to payment record.")

    return {
        "payment_id": payment_id,
        "status": data.get("status", "pending"),
        "type": data.get("type"),
        "amount_paise": data.get("amount_paise"),
        "job_id": data.get("job_id"),
    }
