# src/logger.py

import logging
from .config import LOG_FORMAT

def setup_logger(name: str = "ticketradar") -> logging.Logger:
    """Sets up the main application logger with console logging only."""
    logger = logging.getLogger(name)
    if logger.handlers:
        return logger
    
    logger.setLevel(logging.INFO)
    formatter = logging.Formatter(LOG_FORMAT)
    
    # Console Handler Only
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    return logger

# Root application logger setup
app_logger = setup_logger()

def get_job_logger(job_id: str) -> logging.Logger:
    """
    Creates or retrieves a job-specific logger.
    Logs are printed to the console (stdout) only.
    """
    logger = logging.getLogger(f"job.{job_id}")
    logger.setLevel(logging.INFO)
    # Allow propagation to main logger (so it prints to stdout)
    logger.propagate = True
    return logger


