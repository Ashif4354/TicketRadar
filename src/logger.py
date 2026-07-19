# src/logger.py

import logging
import os
from src.config import LOG_FORMAT, LOG_DIR

# Initialize directory
os.makedirs(LOG_DIR, exist_ok=True)

def setup_logger(name: str = "ticketradar") -> logging.Logger:
    """Sets up the main application logger."""
    logger = logging.getLogger(name)
    if logger.handlers:
        return logger
    
    logger.setLevel(logging.INFO)
    formatter = logging.Formatter(LOG_FORMAT)
    
    # Console Handler
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    # File Handler
    main_log_file = os.path.join(LOG_DIR, "app.log")
    file_handler = logging.FileHandler(main_log_file, encoding="utf-8")
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    
    return logger

# Root application logger setup
app_logger = setup_logger()

def get_job_logger(job_id: str) -> logging.Logger:
    """
    Creates or retrieves a job-specific logger.
    Logs are written to both logs/app.log and logs/job_{job_id}.log
    """
    logger = logging.getLogger(f"job.{job_id}")
    if logger.handlers:
        return logger
        
    logger.setLevel(logging.INFO)
    # Allow propagation to main logger (so it prints to stdout and app.log)
    logger.propagate = True
    
    # Job-specific log file
    job_log_file = os.path.join(LOG_DIR, f"job_{job_id}.log")
    formatter = logging.Formatter(LOG_FORMAT)
    
    try:
        job_file_handler = logging.FileHandler(job_log_file, mode="a", encoding="utf-8")
        job_file_handler.setFormatter(formatter)
        logger.addHandler(job_file_handler)
    except Exception as e:
        app_logger.error(f"Failed to create job logger handler for {job_id}: {e}")
        
    return logger

def get_job_logs(job_id: str, tail_lines: int = 100) -> str:
    """Reads the last tail_lines from the log file for a specific job."""
    job_log_file = os.path.join(LOG_DIR, f"job_{job_id}.log")
    if not os.path.exists(job_log_file):
        return "No log output recorded yet."
    try:
        with open(job_log_file, "r", encoding="utf-8") as f:
            lines = f.readlines()
            return "".join(lines[-tail_lines:])
    except Exception as e:
        return f"Error reading log file: {str(e)}"

def delete_job_log_file(job_id: str) -> None:
    """Clean up log file when a job is deleted."""
    job_log_file = os.path.join(LOG_DIR, f"job_{job_id}.log")
    if os.path.exists(job_log_file):
        try:
            # We close handlers first
            logger = logging.getLogger(f"job.{job_id}")
            for handler in list(logger.handlers):
                handler.close()
                logger.removeHandler(handler)
            os.remove(job_log_file)
        except Exception as e:
            app_logger.error(f"Failed to delete log file for job {job_id}: {e}")
