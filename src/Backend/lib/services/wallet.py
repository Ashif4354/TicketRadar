# src/Backend/lib/services/wallet.py

import logging
import uuid
from typing import Dict, Any, Optional, List
from google.cloud import firestore
from google.api_core.exceptions import Aborted

from ..core.auth import db

logger = logging.getLogger("ticketradar.services.wallet")

class InsufficientFundsError(Exception):
    """Raised when user wallet balance is insufficient for a debit transaction."""
    pass

class WalletService:
    """
    Facade providing atomic, concurrency-safe mutations on the user wallet.
    All balance mutations run inside Firestore transactions with optimistic locking (version).
    Appends an immutable record to wallet_transactions for every credit or debit.
    Enforces deterministic idempotency keys.
    """

    @classmethod
    def get_balance(cls, uid: str) -> int:
        """Returns the current wallet balance in paise (1 credit = 100 paise = ₹1)."""
        if not db:
            logger.warning("Firestore db not available in get_balance.")
            return 0

        doc_ref = db.collection("wallets").document(uid)
        doc = doc_ref.get()
        if doc.exists:
            data = doc.to_dict() or {}
            return int(data.get("balance_paise", 0))
        return 0

    @classmethod
    def get_transactions(cls, uid: str, limit: int = 50) -> List[Dict[str, Any]]:
        """Fetch transaction history for a user sorted by creation time descending."""
        if not db:
            return []

        try:
            query = (
                db.collection("wallet_transactions")
                .where("uid", "==", uid)
                .order_by("created_at", direction=firestore.Query.DESCENDING)
                .limit(limit)
            )
            docs = query.stream()
            txns = []
            for doc in docs:
                item = doc.to_dict() or {}
                if "created_at" in item and item["created_at"]:
                    try:
                        item["created_at"] = item["created_at"].isoformat()
                    except Exception:
                        pass
                txns.append(item)
            return txns
        except Exception as e:
            logger.error(f"Error fetching wallet transactions for {uid}: {e}")
            # Fallback query without composite index requirement
            try:
                docs = db.collection("wallet_transactions").where("uid", "==", uid).stream()
                txns = [d.to_dict() or {} for d in docs]
                txns.sort(key=lambda x: str(x.get("created_at", "")), reverse=True)
                for item in txns[:limit]:
                    if "created_at" in item and item["created_at"]:
                        try:
                            item["created_at"] = item["created_at"].isoformat()
                        except Exception:
                            pass
                return txns[:limit]
            except Exception as fe:
                logger.error(f"Fallback fetch transactions failed: {fe}")
                return []

    @classmethod
    def credit(
        cls,
        uid: str,
        amount_paise: int,
        txn_type: str,
        description: str,
        idempotency_key: str,
        job_id: Optional[str] = None,
        payment_id: Optional[str] = None,
        refund_id: Optional[str] = None,
        created_by: str = "system",
    ) -> Dict[str, Any]:
        """
        Atomically credits paise to user wallet and appends to immutable ledger.
        Safe against duplicate invocations using idempotency_key.
        """
        if amount_paise < 0:
            raise ValueError("Credit amount must be non-negative.")
        return cls._mutate_wallet(
            uid=uid,
            amount_paise=amount_paise,
            direction="CREDIT",
            txn_type=txn_type,
            description=description,
            idempotency_key=idempotency_key,
            job_id=job_id,
            payment_id=payment_id,
            refund_id=refund_id,
            created_by=created_by,
        )

    @classmethod
    def debit(
        cls,
        uid: str,
        amount_paise: int,
        txn_type: str,
        description: str,
        idempotency_key: str,
        job_id: Optional[str] = None,
        created_by: str = "system",
    ) -> Dict[str, Any]:
        """
        Atomically debits paise from user wallet and appends to immutable ledger.
        Raises InsufficientFundsError if wallet balance is less than amount_paise.
        Safe against duplicate invocations using idempotency_key.
        """
        if amount_paise < 0:
            raise ValueError("Debit amount must be non-negative.")
        return cls._mutate_wallet(
            uid=uid,
            amount_paise=amount_paise,
            direction="DEBIT",
            txn_type=txn_type,
            description=description,
            idempotency_key=idempotency_key,
            job_id=job_id,
            created_by=created_by,
        )

    @classmethod
    def _mutate_wallet(
        cls,
        uid: str,
        amount_paise: int,
        direction: str,
        txn_type: str,
        description: str,
        idempotency_key: str,
        job_id: Optional[str] = None,
        payment_id: Optional[str] = None,
        refund_id: Optional[str] = None,
        created_by: str = "system",
        max_retries: int = 5,
    ) -> Dict[str, Any]:
        """Runs the atomic transaction with retry on version conflicts."""
        if not db:
            raise RuntimeError("Firestore database connection is unavailable.")

        # 1. Check idempotency key first (outside transaction to avoid lock contention)
        existing_txns = list(
            db.collection("wallet_transactions")
            .where("idempotency_key", "==", idempotency_key)
            .limit(1)
            .stream()
        )
        if existing_txns:
            existing = existing_txns[0].to_dict() or {}
            logger.info(f"Idempotent replay for key {idempotency_key}. Returning existing txn {existing.get('id')}.")
            return existing

        wallet_ref = db.collection("wallets").document(uid)
        txn_id = str(uuid.uuid4())

        for attempt in range(max_retries):
            try:
                @firestore.transactional
                def _run_in_transaction(transaction):
                    # Check idempotency again within transaction
                    idemp_check = list(
                        db.collection("wallet_transactions")
                        .where("idempotency_key", "==", idempotency_key)
                        .limit(1)
                        .stream(transaction=transaction)
                    )
                    if idemp_check:
                        return idemp_check[0].to_dict()

                    wallet_snap = wallet_ref.get(transaction=transaction)
                    if wallet_snap.exists:
                        data = wallet_snap.to_dict() or {}
                        balance_before = int(data.get("balance_paise", 0))
                        version = int(data.get("version", 0))
                    else:
                        balance_before = 0
                        version = 0

                    if direction == "DEBIT":
                        if balance_before < amount_paise:
                            raise InsufficientFundsError(
                                f"Insufficient wallet balance. Required: ₹{amount_paise/100:.2f}, Available: ₹{balance_before/100:.2f}."
                            )
                        balance_after = balance_before - amount_paise
                    else:
                        balance_after = balance_before + amount_paise

                    new_version = version + 1
                    wallet_update = {
                        "uid": uid,
                        "balance_paise": balance_after,
                        "version": new_version,
                        "updated_at": firestore.SERVER_TIMESTAMP,
                    }
                    if not wallet_snap.exists:
                        wallet_update["created_at"] = firestore.SERVER_TIMESTAMP

                    transaction.set(wallet_ref, wallet_update, merge=True)

                    # Create immutable transaction document
                    txn_doc_ref = db.collection("wallet_transactions").document(txn_id)
                    record = {
                        "id": txn_id,
                        "uid": uid,
                        "type": txn_type,
                        "direction": direction,
                        "amount_paise": amount_paise,
                        "balance_before_paise": balance_before,
                        "balance_after_paise": balance_after,
                        "description": description,
                        "job_id": job_id,
                        "payment_id": payment_id,
                        "refund_id": refund_id,
                        "idempotency_key": idempotency_key,
                        "created_at": firestore.SERVER_TIMESTAMP,
                        "created_by": created_by,
                    }
                    transaction.set(txn_doc_ref, record)
                    from datetime import datetime, timezone
                    ret_record = dict(record)
                    ret_record["created_at"] = datetime.now(timezone.utc).isoformat()
                    return ret_record

                result = _run_in_transaction(db.transaction())
                return result

            except InsufficientFundsError:
                raise
            except Aborted as e:
                logger.warning(f"Wallet transaction conflict on attempt {attempt+1}/{max_retries} for uid {uid}: {e}")
                if attempt == max_retries - 1:
                    raise
            except Exception as e:
                # If error is from InsufficientFunds, let it through
                if "Insufficient wallet balance" in str(e):
                    raise InsufficientFundsError(str(e))
                logger.error(f"Wallet transaction error for uid {uid}: {e}")
                raise
