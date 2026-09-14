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

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

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

# Initialize logger
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("ticketradar.api")

manager = JobManager()


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield
    # Shutdown: Signal all running job loops to stop gracefully for server shutdown
    logger.info("Shutting down backend app...")
    manager.stop_all_jobs_for_shutdown()


app = FastAPI(
    title="TicketRadar API",
    description="Backend API for TicketRadar movie ticket monitoring",
    version="0.1.0",
    lifespan=lifespan
)

# Enable CORS for development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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
        content={"status": "ok", "service": "TicketRadar API", "version": "0.1.0"}
    )


if __name__ == "__main__":
    import uvicorn
    is_frozen = getattr(sys, "frozen", False) or "__compiled__" in globals()
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=not is_frozen)
