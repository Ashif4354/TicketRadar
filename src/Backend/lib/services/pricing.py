# src/Backend/lib/services/pricing.py

import logging
import uuid
from typing import Dict, Any, List
from google.cloud import firestore

from ..core.auth import db

logger = logging.getLogger("ticketradar.services.pricing")

DEFAULT_PRICES = {
    "sms_paise": 50,         # ₹0.50
    "whatsapp_paise": 100,   # ₹1.00
    "phone_call_paise": 150, # ₹1.50
    "email_paise": 0,        # Free
    "discord_paise": 0,      # Free
}

class PricingService:
    """
    Manages notification pricing configurations.
    Maintains historical records in notification_price_configs.
    All admin price modifications write an immutable record into admin_audit_logs.
    """

    @classmethod
    def get_current_prices(cls) -> Dict[str, Any]:
        """
        Retrieves the current active notification pricing config.
        If no configuration exists, seeds default prices.
        """
        if not db:
            return {
                "id": "default",
                **DEFAULT_PRICES,
                "is_current": True,
                "note": "Default system prices",
            }

        try:
            docs = list(
                db.collection("notification_price_configs")
                .where("is_current", "==", True)
                .limit(1)
                .stream()
            )
            if docs:
                data = docs[0].to_dict() or {}
                return data

            # Seed default configuration
            config_id = str(uuid.uuid4())
            new_config = {
                "id": config_id,
                **DEFAULT_PRICES,
                "is_current": True,
                "effective_from": firestore.SERVER_TIMESTAMP,
                "superseded_at": None,
                "updated_by": "system",
                "note": "Initial system pricing config",
                "created_at": firestore.SERVER_TIMESTAMP,
            }
            db.collection("notification_price_configs").document(config_id).set(new_config)
            from datetime import datetime, timezone
            now_iso = datetime.now(timezone.utc).isoformat()
            ret_config = dict(new_config)
            ret_config["effective_from"] = now_iso
            ret_config["created_at"] = now_iso
            return ret_config
        except Exception as e:
            logger.error(f"Error fetching current pricing: {e}")
            return {
                "id": "fallback",
                **DEFAULT_PRICES,
                "is_current": True,
                "note": "Fallback prices due to database error",
            }

    @classmethod
    def get_price_for_medium(cls, medium: str) -> tuple[int, str]:
        """
        Returns (price_paise, config_id) for the specified notification medium.
        """
        config = cls.get_current_prices()
        config_id = config.get("id", "default")
        norm = medium.strip().lower().replace(" ", "_")

        if "sms" in norm:
            return int(config.get("sms_paise", DEFAULT_PRICES["sms_paise"])), config_id
        elif "whatsapp" in norm:
            return int(config.get("whatsapp_paise", DEFAULT_PRICES["whatsapp_paise"])), config_id
        elif "call" in norm or "phone" in norm:
            return int(config.get("phone_call_paise", DEFAULT_PRICES["phone_call_paise"])), config_id
        elif "email" in norm:
            return int(config.get("email_paise", 0)), config_id
        elif "discord" in norm:
            return int(config.get("discord_paise", 0)), config_id
        return 0, config_id

    @classmethod
    def update_prices(
        cls,
        admin_uid: str,
        admin_email: str,
        sms_paise: int,
        whatsapp_paise: int,
        phone_call_paise: int,
        note: str,
    ) -> Dict[str, Any]:
        """
        Atomically supersedes the current pricing config with a new one and records an audit log.
        A non-empty explanation note is mandatory.
        """
        if not note or not note.strip():
            raise ValueError("An explanation note is required when updating notification prices.")

        if sms_paise < 0 or whatsapp_paise < 0 or phone_call_paise < 0:
            raise ValueError("Pricing amounts must be non-negative integer paise.")

        if not db:
            raise RuntimeError("Database connection unavailable.")

        batch = db.batch()

        # 1. Supersede existing current configs
        current_docs = list(
            db.collection("notification_price_configs")
            .where("is_current", "==", True)
            .stream()
        )
        old_prices = {}
        for doc in current_docs:
            old_prices = doc.to_dict() or {}
            batch.update(doc.reference, {
                "is_current": False,
                "superseded_at": firestore.SERVER_TIMESTAMP,
            })

        # 2. Insert new config
        new_config_id = str(uuid.uuid4())
        new_config_ref = db.collection("notification_price_configs").document(new_config_id)
        new_config = {
            "id": new_config_id,
            "sms_paise": int(sms_paise),
            "whatsapp_paise": int(whatsapp_paise),
            "phone_call_paise": int(phone_call_paise),
            "email_paise": 0,
            "discord_paise": 0,
            "is_current": True,
            "effective_from": firestore.SERVER_TIMESTAMP,
            "superseded_at": None,
            "updated_by": admin_uid,
            "note": note.strip(),
            "created_at": firestore.SERVER_TIMESTAMP,
        }
        batch.set(new_config_ref, new_config)

        # 3. Create audit log entry
        audit_log_id = str(uuid.uuid4())
        audit_log_ref = db.collection("admin_audit_logs").document(audit_log_id)
        audit_entry = {
            "id": audit_log_id,
            "admin_uid": admin_uid,
            "admin_email": admin_email,
            "action_type": "PRICE_UPDATED",
            "old_value": old_prices,
            "new_value": new_config,
            "reason": note.strip(),
            "created_at": firestore.SERVER_TIMESTAMP,
        }
        batch.set(audit_log_ref, audit_entry)

        batch.commit()
        logger.info(f"Notification pricing updated by admin {admin_uid}: new_config_id={new_config_id}")
        from datetime import datetime, timezone
        ret_config = dict(new_config)
        ret_config["effective_from"] = datetime.now(timezone.utc).isoformat()
        ret_config["created_at"] = datetime.now(timezone.utc).isoformat()
        return ret_config

    @classmethod
    def get_price_history(cls, limit: int = 50) -> List[Dict[str, Any]]:
        """Returns historical pricing configs."""
        if not db:
            return []
        try:
            docs = (
                db.collection("notification_price_configs")
                .order_by("created_at", direction=firestore.Query.DESCENDING)
                .limit(limit)
                .stream()
            )
            res = []
            for doc in docs:
                d = doc.to_dict() or {}
                for k in ("effective_from", "superseded_at", "created_at"):
                    if k in d and d[k]:
                        try:
                            d[k] = d[k].isoformat()
                        except Exception:
                            pass
                res.append(d)
            return res
        except Exception as e:
            logger.error(f"Error fetching price history: {e}")
            return []
