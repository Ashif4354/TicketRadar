# src/Backend/api/routers/wallet.py

import logging
import uuid
from fastapi import APIRouter, HTTPException, Depends
from google.cloud import firestore

from lib.core.auth import get_authorized_user, db
from lib.utils.config import settings
from lib.services.wallet import WalletService
from lib.services.gcp_logger import gcp_logger
from lib.providers.payment.factory import PaymentGatewayFactory
from api.dependencies import require_payments_enabled, get_user_details, require_terms_accepted
from api.schemas import WalletTopupRequest

logger = logging.getLogger("ticketradar.api.wallet")

router = APIRouter(
    prefix="/api/wallet",
    tags=["Wallet"],
    dependencies=[Depends(require_payments_enabled), Depends(get_authorized_user)]
)

@router.get("/balance")
async def get_wallet_balance(claims: dict = Depends(get_authorized_user)):
    """Returns the user's current wallet balance."""
    uid = claims.get("uid")
    if not uid:
        raise HTTPException(status_code=401, detail="User identification missing.")

    balance_paise = WalletService.get_balance(uid)
    return {
        "uid": uid,
        "balance_paise": balance_paise,
        "balance_inr": round(balance_paise / 100.0, 2),
    }

@router.get("/transactions")
async def get_wallet_transactions(claims: dict = Depends(get_authorized_user)):
    """Returns the user's immutable wallet transaction history."""
    uid = claims.get("uid")
    if not uid:
        raise HTTPException(status_code=401, detail="User identification missing.")

    txns = WalletService.get_transactions(uid)
    return txns

@router.post("/topup/initiate")
async def initiate_topup(
    payload: WalletTopupRequest,
    claims: dict = Depends(get_authorized_user)
):
    """
    Creates a payment order via the active payment gateway for topping up the user's wallet.
    Upon successful payment, the gateway webhook will credit the wallet.
    """
    await require_terms_accepted(claims)
    uid = claims.get("uid")
    _, email, _ = get_user_details(uid, claims)

    amount_paise = payload.amount_paise
    if amount_paise < 100:
        raise HTTPException(status_code=400, detail="Minimum top-up amount is ₹1.00 (100 paise).")

    payment_id = str(uuid.uuid4())
    idempotency_key = f"topup_{payment_id}"

    # Record pending payment in Firestore
    if db:
        try:
            active_gw = (settings.payment_gateway if settings else "cashfree").strip().lower()
            db.collection("payments").document(payment_id).set({
                "id": payment_id,
                "uid": uid,
                "type": "WALLET_TOPUP",
                "amount_paise": amount_paise,
                "status": "pending",
                "payment_method": "gateway",
                "gateway_name": active_gw,
                "gateway_order_id": idempotency_key,
                "idempotency_key": idempotency_key,
                "created_at": firestore.SERVER_TIMESTAMP,
            })
        except Exception as e:
            logger.error(f"Failed to record pending payment doc: {e}")

    try:
        gateway = PaymentGatewayFactory.create()
        order_res = await gateway.create_order(
            amount_paise=amount_paise,
            idempotency_key=idempotency_key,
            customer_uid=uid,
            customer_email=email or "user@ticketradar.local",
            metadata={
                "type": "WALLET_TOPUP",
                "payment_id": payment_id,
                "return_url": "",
            }
        )

        if db:
            db.collection("payments").document(payment_id).update({
                "gateway_session_id": order_res.session_token,
                "checkout_url": order_res.checkout_url,
            })

        gcp_logger.log_event(
            "Wallet Topup Initiated",
            user_id=uid,
            details={
                "payment_id": payment_id,
                "order_id": order_res.order_id,
                "amount_paise": amount_paise,
                "amount_inr": round(amount_paise / 100.0, 2),
                "gateway": active_gw,
            }
        )

        return {
            "payment_id": payment_id,
            "order_id": order_res.order_id,
            "session_token": order_res.session_token,
            "checkout_url": order_res.checkout_url,
            "amount_paise": amount_paise,
            "amount_inr": round(amount_paise / 100.0, 2),
        }
    except Exception as e:
        logger.error(f"Error initiating payment order: {e}")
        if db:
            db.collection("payments").document(payment_id).update({"status": "failed"})
        raise HTTPException(status_code=500, detail=f"Failed to initiate payment: {str(e)}")
