# src/Backend/lib/utils/redact.py

import re

def redact_phone(phone: str | None) -> str:
    """
    Redacts a phone number to prevent PII exposure in logs and audit trails.
    Example: '+919876543210' -> '+91XXXXXX3210'
    """
    if not phone:
        return "[EMPTY]"
    phone_clean = str(phone).strip()
    if len(phone_clean) >= 10:
        last4 = phone_clean[-4:]
        prefix = phone_clean[:-4]
        # Keep country code if present (e.g. +91)
        if prefix.startswith("+"):
            return f"{prefix[:3]}XXXXXX{last4}"
        return f"XXXXXX{last4}"
    return "XXXX" + phone_clean[-2:] if len(phone_clean) > 2 else "[REDACTED]"


def redact_email(email: str | None) -> str:
    """
    Redacts an email address to prevent PII exposure in logs.
    Example: 'user@example.com' -> 'u***@example.com'
    """
    if not email:
        return "[EMPTY]"
    email_clean = str(email).strip()
    if "@" not in email_clean:
        return "[REDACTED]"
    parts = email_clean.split("@", 1)
    name, domain = parts[0], parts[1]
    if len(name) <= 1:
        masked_name = "*"
    elif len(name) == 2:
        masked_name = name[0] + "*"
    else:
        masked_name = name[0] + "***" + name[-1]
    return f"{masked_name}@{domain}"
