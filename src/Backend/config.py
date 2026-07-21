# src/config.py

import os
import sys
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field
import platformdirs

# Get user data directory
USER_DATA_DIR = platformdirs.user_data_dir(appname="TicketRadar", appauthor="DarkGlance")
os.makedirs(USER_DATA_DIR, exist_ok=True)

# Get absolute path to project root
if "__compiled__" in globals() or hasattr(sys, "frozen"):
    BASE_DIR = os.path.dirname(os.path.abspath(sys.executable))
else:
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

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
    default_check_interval: int = Field(default=30)

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
LOG_DIR = USER_DATA_DIR

# Ensure logs directory exists
os.makedirs(LOG_DIR, exist_ok=True)
