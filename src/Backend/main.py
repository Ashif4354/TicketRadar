# src/Backend/main.py

import os
import sys
import logging
from contextlib import asynccontextmanager

# Ensure backend directory is in Python path to support imports
backend_dir = os.path.dirname(os.path.abspath(__file__))
root_dir = os.path.abspath(os.path.join(backend_dir, "..", ".."))
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

import time
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from lib.utils.config import LOG_FORMAT, settings
from lib.core.monitor import JobManager
from api.routers import (
    config,
    jobs,
    auth,
    admin,
    bms_proxy,
    wallet,
    payments,
    profile,
    consent,
    terms,
    twilio_webhooks,
    cashfree_webhooks,
)

from lib.utils.logger import configure_logging

# Configure centralized logging (console standard, file in src/Backend/logs, GCP logging attached)
configure_logging(enable_atatus_file_correlation=False)
logger = logging.getLogger("ticketradar.api")

# Determine application version from pyproject.toml
def get_app_version(default: str = "2.0.0") -> str:
    candidate_paths = [
        os.path.join(backend_dir, "pyproject.toml"),
        os.path.join(root_dir, "pyproject.toml"),
        os.path.join(root_dir, "src", "Backend", "pyproject.toml"),
    ]
    for path in candidate_paths:
        if os.path.exists(path):
            try:
                import tomllib
                with open(path, "rb") as f:
                    data = tomllib.load(f)
                    version = data.get("project", {}).get("version")
                    if version:
                        return str(version)
            except Exception:
                pass
    try:
        from importlib.metadata import version
        return version("ticketradar")
    except Exception:
        pass
    return default

APP_VERSION = get_app_version()

# Environment taken from settings
ENVIRONMENT = settings.environment if settings else "development"

# Initialize Atatus APM Agent if license key is provided in settings.
# Note: Initialization should be done before "app = FastAPI()", and not in lifespan.
atatus_client = None
if settings and settings.atatus_license_key:
    try:
        import atatus
        from atatus.contrib.starlette import create_client

        atatus_client = atatus.get_client()
        if atatus_client is None:
            app_name = settings.atatus_app_name if (settings and settings.atatus_app_name) else "TicketRadar"

            atatus_client = create_client({
                "APP_NAME": app_name,
                "LICENSE_KEY": settings.atatus_license_key,
                "APP_VERSION": APP_VERSION,
                "ENVIRONMENT": ENVIRONMENT,
                "TRACING": True,
                "ANALYTICS": True,
                "ANALYTICS_CAPTURE_OUTGOING": True,
                "LOG_BODY": "all",
            })
            # Enable Atatus log correlation exclusively on the file handler (console remains clean)
            configure_logging(enable_atatus_file_correlation=True)
            logger.info("Atatus APM agent initialized successfully with file log correlation.")
    except Exception as e:
        logger.error(f"Failed to initialize Atatus APM client: {e}")
        atatus_client = None
else:
    logger.info("Atatus license key not provided in settings; Atatus instrumentation is disabled.")

manager = JobManager()


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield
    # Shutdown: Signal all running job loops to stop gracefully for server shutdown
    logger.info("Shutting down backend app...")
    manager.stop_all_jobs_for_shutdown()
    if atatus_client is not None:
        try:
            atatus_client.close()
        except Exception:
            pass


app = FastAPI(
    title="TicketRadar API",
    description="Backend API for TicketRadar movie ticket monitoring",
    version=APP_VERSION,
    lifespan=lifespan
)

# Endpoint access logging middleware (captures all endpoint requests)
@app.middleware("http")
async def log_endpoint_requests(request: Request, call_next):
    start_time = time.perf_counter()
    method = request.method
    path = request.url.path
    query = request.url.query
    full_path = f"{path}?{query}" if query else path

    try:
        response = await call_next(request)
        duration_ms = (time.perf_counter() - start_time) * 1000
        logger.info(f"{method} {full_path} - {response.status_code} ({duration_ms:.2f}ms)")
        return response
    except Exception as exc:
        duration_ms = (time.perf_counter() - start_time) * 1000
        logger.error(f"{method} {full_path} - error: {exc} ({duration_ms:.2f}ms)", exc_info=True)
        raise

# Enable CORS for development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add Atatus middleware
# Note: Make sure to add Atatus middleware as the last middleware in your app
if atatus_client is not None:
    from atatus.contrib.starlette import Atatus
    app.add_middleware(Atatus, client=atatus_client)

# Register API Routers
app.include_router(config.router)
app.include_router(jobs.router)
app.include_router(auth.router)
app.include_router(admin.router)
app.include_router(bms_proxy.router)
app.include_router(wallet.router)
app.include_router(payments.router)
app.include_router(profile.router)
app.include_router(consent.router)
app.include_router(terms.router)
app.include_router(twilio_webhooks.router)
app.include_router(cashfree_webhooks.router)



@app.get("/")
async def root():
    return JSONResponse(
        status_code=200,
        content={"message": "TicketRadar API is active."}
    )


@app.get("/health")
async def health():
    return JSONResponse(
        status_code=200,
        content={"status": "ok", "service": "TicketRadar API", "version": APP_VERSION}
    )


if __name__ == "__main__":
    import uvicorn
    is_frozen = getattr(sys, "frozen", False) or "__compiled__" in globals()
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=not is_frozen, log_config=None)
