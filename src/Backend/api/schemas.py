# src/Backend/api/schemas.py

from typing import Dict, Any, List
from pydantic import BaseModel, Field


class TestAlertRequest(BaseModel):
    medium: str = Field(..., description="Alert medium: 'email' or 'discord'")
    target: str = Field(..., description="Target email address or webhook URL")
    recaptcha_token: str = Field(default="", description="Google reCAPTCHA token")


class JobParams(BaseModel):
    url: str
    date_str: str
    theatres: List[str]


class CreateJobRequest(BaseModel):
    service_provider: str = "BookMyShow"
    notification_medium: str
    notification_config: Dict[str, Any]
    check_interval: int = Field(default=60, ge=60, description="Check interval in seconds (minimum 60s / 1 min)")
    params: JobParams
    recaptcha_token: str = Field(default="", description="Google reCAPTCHA token")


class UpdateRoleRequest(BaseModel):
    role: str


class RequestAccessPayload(BaseModel):
    recaptcha_token: str = Field(default="", description="Google reCAPTCHA token")
