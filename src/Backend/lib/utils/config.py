# src/config.py

import os
import sys
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field
import platformdirs

# Get user data directory
USER_DATA_DIR = platformdirs.user_data_dir(appname="TicketRadar", appauthor="DarkGlance")
os.makedirs(USER_DATA_DIR, exist_ok=True)

# Get absolute path to backend directory (or executable directory if compiled)
if "__compiled__" in globals() or hasattr(sys, "frozen"):
    BASE_DIR = os.path.dirname(os.path.abspath(sys.executable))
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Check locations for .env file in order
locations = [
    os.path.join(USER_DATA_DIR, ".env"),
    os.path.join(BASE_DIR, ".env"),
    os.path.join(os.getcwd(), ".env"),
]

# If running compiled/frozen from 'dist' directory, look in the parent directory for .env
if ("__compiled__" in globals() or hasattr(sys, "frozen")) and os.path.basename(BASE_DIR) == "dist":
    locations.append(os.path.join(os.path.dirname(BASE_DIR), ".env"))

ENV_FILE_PATH = None
for loc in locations:
    if os.path.exists(loc):
        ENV_FILE_PATH = loc
        break

if not ENV_FILE_PATH:
    ENV_FILE_PATH = os.path.join(BASE_DIR, ".env")

class Settings(BaseSettings):
    # SMTP Configuration
    smtp_server: str = Field(default="smtp.gmail.com")
    smtp_port: int = Field(default=587)
    smtp_email: str
    smtp_password: str

    # Scraper Settings
    default_check_interval: int = Field(default=60)

    # Security Settings
    disable_security: bool = Field(default=False)

    # reCAPTCHA Configuration
    recaptcha_site: str = Field(default="6LfUdl0tAAAAALD21Jd3geQFRavY8xeWMbadKybZ")
    recaptcha_secret: str = Field(default="6LfUdl0tAAAAAAjyjVtoGRY2cY52NJUOhc4R3mLu")

    # Firebase Configuration
    firebase_type: str = Field(default="")
    firebase_project_id: str = Field(default="")
    firebase_private_key_id: str = Field(default="")
    firebase_private_key: str = Field(default="")
    firebase_client_email: str = Field(default="")
    firebase_client_id: str = Field(default="")
    firebase_auth_uri: str = Field(default="")
    firebase_token_uri: str = Field(default="")
    firebase_auth_provider_x509_cert_url: str = Field(default="")
    firebase_client_x509_cert_url: str = Field(default="")
    firebase_universe_domain: str = Field(default="")

    # Admin Discord Webhook Configuration
    admin_discord_webhook_url: str = Field(default="")

    # Google Cloud Logging Configuration
    gcp_logging_type: str = Field(default="service_account")
    gcp_logging_project_id: str = Field(default="")
    gcp_logging_private_key_id: str = Field(default="")
    gcp_logging_private_key: str = Field(default="")
    gcp_logging_client_email: str = Field(default="")
    gcp_logging_client_id: str = Field(default="")
    gcp_logging_auth_uri: str = Field(default="")
    gcp_logging_token_uri: str = Field(default="")
    gcp_logging_auth_provider_x509_cert_url: str = Field(default="")
    gcp_logging_client_x509_cert_url: str = Field(default="")
    gcp_logging_universe_domain: str = Field(default="")

    # Use pydantic configuration to load from .env
    model_config = SettingsConfigDict(
        env_file=ENV_FILE_PATH,
        env_file_encoding="utf-8",
        # Case insensitive mapping (so SMTP_SERVER matches smtp_server)
        case_sensitive=False,
        extra="ignore"
    )


# Instantiate settings gracefully
try:
    settings = Settings()
    config_error = None
except Exception as e:
    settings = None
    config_error = str(e)

# Application Constants
LOG_FORMAT = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
