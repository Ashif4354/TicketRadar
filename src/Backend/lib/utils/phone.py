# src/Backend/lib/utils/phone.py

import phonenumbers
from phonenumbers import NumberParseException, PhoneNumberFormat

def normalize_indian_phone(phone_input: str) -> str:
    """
    Normalizes an Indian phone number to E.164 format (+91XXXXXXXXXX).
    Strictly validates that the number is a valid Indian (+91) phone number.
    Raises ValueError if invalid.
    """
    if not phone_input or not isinstance(phone_input, str):
        raise ValueError("Phone number is required.")

    cleaned = phone_input.strip()
    try:
        parsed = phonenumbers.parse(cleaned, "IN")
    except NumberParseException as e:
        raise ValueError(f"Invalid phone number format: {e}")

    if not phonenumbers.is_valid_number(parsed):
        raise ValueError("Invalid phone number.")

    if parsed.country_code != 91:
        raise ValueError("Only Indian phone numbers (+91) are currently supported.")

    national_number = str(parsed.national_number)
    # Indian mobile numbers are 10 digits starting with 6, 7, 8, or 9
    if len(national_number) != 10 or national_number[0] not in "6789":
        raise ValueError("Must be a valid 10-digit Indian mobile number starting with 6, 7, 8, or 9.")

    return phonenumbers.format_number(parsed, PhoneNumberFormat.E164)


def validate_phone(phone_input: str) -> bool:
    """
    Checks if a given phone number is a valid Indian mobile number.
    Returns True if valid, False otherwise.
    """
    try:
        normalize_indian_phone(phone_input)
        return True
    except Exception:
        return False
