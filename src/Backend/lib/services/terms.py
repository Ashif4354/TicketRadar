# src/Backend/lib/services/terms.py

import logging
from google.cloud import firestore
from ..core.auth import db, is_security_disabled
from ..utils.config import settings

logger = logging.getLogger("ticketradar.services.terms")

class TermsService:
    """
    Manages acceptance and version tracking for Terms of Service and Privacy Policy.
    """

    @classmethod
    def get_current_version(cls) -> str:
        return settings.current_terms_version if settings else "2.0"

    @classmethod
    def check_terms_accepted(cls, uid: str) -> bool:
        """
        Returns True if the user has accepted the current terms version.
        """
        if is_security_disabled() or not db or not uid or uid == "dev-user-001":
            return True

        current_ver = cls.get_current_version()
        try:
            doc = db.collection("users").document(uid).get()
            if not doc.exists:
                return False
            data = doc.to_dict() or {}
            accepted_ver = data.get("terms_version_accepted")
            return accepted_ver == current_ver
        except Exception as e:
            logger.error(f"Error checking terms acceptance for {uid}: {e}")
            return False

    @classmethod
    def accept_terms(cls, uid: str, version: str) -> bool:
        """
        Records the user's acceptance of the specified terms version.
        """
        if not db or not uid:
            return False

        try:
            db.collection("users").document(uid).set({
                "uid": uid,
                "terms_version_accepted": version,
                "terms_accepted_at": firestore.SERVER_TIMESTAMP,
                "updated_at": firestore.SERVER_TIMESTAMP,
            }, merge=True)
            logger.info(f"User {uid} accepted Terms version {version}.")
            return True
        except Exception as e:
            logger.error(f"Error recording terms acceptance for {uid}: {e}")
            return False
