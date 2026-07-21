# src/logger.py

import logging
import re
import os
from .config import LOG_FORMAT, LOG_DIR

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
    """Reads the last tail_lines from the log file for a specific job (raw, for developers)."""
    job_log_file = os.path.join(LOG_DIR, f"job_{job_id}.log")
    if not os.path.exists(job_log_file):
        return "No log output recorded yet."
    try:
        with open(job_log_file, "r", encoding="utf-8") as f:
            lines = f.readlines()
            return "".join(lines[-tail_lines:])
    except Exception as e:
        return f"Error reading log file: {str(e)}"


# Matches: "2026-07-20 10:05:00,123 [LEVEL] logger.name: message"
_LOG_LINE_RE = re.compile(
    r"^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2},\d+ \[(?P<level>\w+)\] [^:]+: (?P<msg>.+)$"
)
# Levels shown to the user — DEBUG is for developers only
_USER_LEVELS = {"INFO", "WARNING", "ERROR", "CRITICAL"}


def get_job_logs_user(job_id: str, tail_lines: int = 60) -> str:
    """
    Returns the last tail_lines of user-facing log lines for a job.
    Strips the technical prefix (timestamp, logger name) and excludes DEBUG lines,
    so only clean, readable messages are shown in the UI.
    """
    job_log_file = os.path.join(LOG_DIR, f"job_{job_id}.log")
    if not os.path.exists(job_log_file):
        return "No activity recorded yet."
    try:
        with open(job_log_file, "r", encoding="utf-8") as f:
            raw_lines = f.readlines()

        user_lines = []
        for line in raw_lines:
            line = line.rstrip()
            m = _LOG_LINE_RE.match(line)
            if m and m.group("level") in _USER_LEVELS:
                user_lines.append(m.group("msg"))
            # Lines that don't match the pattern (e.g. multi-line tracebacks) are skipped

        if not user_lines:
            return "No activity recorded yet."

        return "\n".join(user_lines[-tail_lines:])
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
