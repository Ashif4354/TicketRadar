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

# Check for .env in user data directory first, fallback to base directory
ENV_FILE_PATH = os.path.join(USER_DATA_DIR, ".env")
if not os.path.exists(ENV_FILE_PATH):
    ENV_FILE_PATH = os.path.join(BASE_DIR, ".env")

class Settings(BaseSettings):
    # SMTP Configuration
    smtp_server: str
    smtp_port: int
    smtp_email: str
    smtp_password: str

    # Scraper Settings
    default_check_interval: int = Field(default=30)
    default_playwright_timeout: int = Field(default=20000)  # ms
    playwright_headless: bool = Field(default=True)
    playwright_channel: str = Field(default="chrome")

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
