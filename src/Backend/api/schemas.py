# src/Backend/api/schemas.py

from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field

class TestAlertRequest(BaseModel):
    medium: str = Field(..., description="Alert medium: 'email', 'discord', 'sms', 'whatsapp', 'phone_call'")
    target: str = Field(..., description="Target email address, webhook URL, or E.164 phone number")
    recaptcha_token: str = Field(default="", description="Google reCAPTCHA token")

class JobParams(BaseModel):
    url: str
    date_str: str
    theatres: List[str]
    language: Optional[str] = None
    format: Optional[str] = None

class CreateJobRequest(BaseModel):
    service_provider: str = "BookMyShow"
    notification_medium: str
    notification_config: Dict[str, Any]
    check_interval: int = Field(default=60, ge=60, description="Check interval in seconds (minimum 60s / 1 min)")
    params: JobParams
    recaptcha_token: str = Field(default="", description="Google reCAPTCHA token")
    # Payment & Multi-channel configuration
    payment_method: str = Field(default="wallet", description="Payment method: 'wallet', 'cashfree', or 'free'")
    phone_number: Optional[str] = Field(default=None, description="E.164 phone number for SMS, WhatsApp, or Phone Call")
    sms_consent: bool = Field(default=False, description="Consent for SMS alerts")
    whatsapp_consent: bool = Field(default=False, description="Consent for WhatsApp alerts")
    call_consent: bool = Field(default=False, description="Consent for automated phone calls")

class UpdateJobRequest(BaseModel):
    service_provider: str = "BookMyShow"
    notification_medium: str
    notification_config: Dict[str, Any]
    check_interval: int = Field(default=60, ge=60, description="Check interval in seconds (minimum 60s / 1 min)")
    params: JobParams

class UpdateRoleRequest(BaseModel):
    role: str

class RequestAccessPayload(BaseModel):
    recaptcha_token: str = Field(default="", description="Google reCAPTCHA token")

class WalletTopupRequest(BaseModel):
    amount_paise: int = Field(..., ge=100, description="Amount in paise (minimum 100 paise = ₹1.00)")

class UpdatePricesRequest(BaseModel):
    sms_paise: int = Field(..., ge=0)
    whatsapp_paise: int = Field(..., ge=0)
    phone_call_paise: int = Field(..., ge=0)
    note: str = Field(..., min_length=3, description="Audit explanation for price change")

class AdminAdjustWalletRequest(BaseModel):
    amount_paise: int = Field(..., gt=0)
    direction: str = Field(..., pattern="^(CREDIT|DEBIT)$")
    reason: str = Field(..., min_length=3, description="Mandatory audit explanation for balance adjustment")

class AdminCashfreeRefundRequest(BaseModel):
    order_id: str = Field(..., description="Cashfree order ID")
    amount_paise: int = Field(..., gt=0)
    reason: str = Field(..., min_length=3)
    job_id: Optional[str] = None

class UpdateNotificationPreferencesRequest(BaseModel):
    phone_number: Optional[str] = None
    email_enabled: Optional[bool] = None
    email_address: Optional[str] = None
    discord_enabled: Optional[bool] = None
    discord_webhook_url: Optional[str] = None
    whatsapp_enabled: Optional[bool] = None
    whatsapp_phone: Optional[str] = None
    phone_call_enabled: Optional[bool] = None
    call_phone: Optional[str] = None
    sms_enabled: Optional[bool] = None
    sms_phone: Optional[str] = None
    email_fallback_on_no_answer: Optional[bool] = None
    preferred_medium: Optional[str] = None

class OptInRequest(BaseModel):
    phone_number: Optional[str] = None

class AcceptTermsRequest(BaseModel):
    version: str = Field(default="2.0")
