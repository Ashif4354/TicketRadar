# src/Backend/tests/test_concurrency.py

import pytest
import asyncio
from unittest.mock import MagicMock
from google.api_core.exceptions import Aborted

from lib.services.wallet import WalletService, InsufficientFundsError
from lib.services import wallet as wallet_service_module
from lib.core.job import MonitorJob
from lib.core.monitor import JobManager

manager = JobManager()

@pytest.mark.asyncio
async def test_wallet_two_concurrent_debits():
    """
    Two concurrent debits competing for the same balance.
    With balance = 100 paise, both attempt to debit 100 paise.
    Exactly one must succeed, and one must raise InsufficientFundsError.
    Total balance afterwards must be 0, not negative.
    """
    uid = "user-concurrent-debits"
    # Credit 100 paise
    WalletService.credit(
        uid=uid,
        amount_paise=100,
        txn_type="WALLET_TOPUP",
        description="Seed 100 paise",
        idempotency_key="seed_concurrent_1"
    )
    assert WalletService.get_balance(uid) == 100

    results = []
    errors = []

    def run_debit(idemp_key):
        try:
            res = WalletService.debit(
                uid=uid,
                amount_paise=100,
                txn_type="JOB_PAYMENT",
                description="Concurrent debit",
                idempotency_key=idemp_key
            )
            results.append(res)
        except Exception as ex:
            errors.append(ex)

    loop = asyncio.get_running_loop()
    await asyncio.gather(
        loop.run_in_executor(None, run_debit, "concurrent_key_a"),
        loop.run_in_executor(None, run_debit, "concurrent_key_b"),
    )

    # Exactly one succeeded and one failed with InsufficientFundsError
    assert len(results) == 1
    assert len(errors) == 1
    assert isinstance(errors[0], InsufficientFundsError)
    assert WalletService.get_balance(uid) == 0


def test_wallet_version_conflict_retries(monkeypatch):
    """
    Simulates a transient Aborted conflict on the first transaction attempt.
    The retry loop in WalletService must catch it and succeed on the next attempt.
    """
    uid = "user-retry-test"
    WalletService.credit(
        uid=uid,
        amount_paise=500,
        txn_type="WALLET_TOPUP",
        description="Topup for retry test",
        idempotency_key="seed_retry_1"
    )

    attempts = {"count": 0}
    orig_transaction = wallet_service_module.db.transaction

    def mock_flaky_transaction():
        attempts["count"] += 1
        if attempts["count"] == 1:
            raise Aborted("Simulated concurrent transaction conflict")
        return orig_transaction()

    monkeypatch.setattr(wallet_service_module.db, "transaction", mock_flaky_transaction)

    res = WalletService.debit(
        uid=uid,
        amount_paise=200,
        txn_type="JOB_PAYMENT",
        description="Debit with retry",
        idempotency_key="retry_debit_key_1"
    )
    assert res["balance_after_paise"] == 300
    assert attempts["count"] >= 2
    assert WalletService.get_balance(uid) == 300


@pytest.mark.asyncio
async def test_job_cancel_while_dispatching(async_client):
    """
    Tests the race condition where a user attempts to DELETE /api/jobs/{id}
    while the job's notification status is 'dispatched'.
    Server must respond with HTTP 409 Conflict, refuse deletion, and not refund.
    """
    uid = "test-user-uid-123"
    job_id = "job-race-1"

    # Create job in manager and db with notification_status='dispatched'
    job = MonitorJob(
        job_id=job_id,
        params={
            "url": "https://in.bookmyshow.com/movies/buytickets/ET12345678/20260719",
            "date_str": "20260719",
            "theatres": ["PVR Velachery"]
        },
        notification_medium="SMS",
        notification_config={"phone_number": "+919876543210"},
        created_by=uid,
        price_paise=150
    )
    job.status = "Running"
    job.notification_status = "dispatched"
    manager.jobs[job_id] = job
    manager._save_job_to_firestore(job)

    # DELETE request
    res = await async_client.delete(f"/api/jobs/{job_id}")
    assert res.status_code == 409
    assert "Notification is currently being dispatched" in res.json()["detail"]

    # Clean up
    job.notification_status = "pending"
    manager.delete_job(job_id)


def test_event_opens_while_cancelling():
    """
    Tests the race condition where BMS tickets open (scraper returns success)
    while a job is being cancelled (status='Cancelling' or 'Stopped').
    claim_notification_slot must return False and prevent dispatch.
    """
    job_id = "job-race-2"
    job = MonitorJob(
        job_id=job_id,
        params={
            "url": "https://in.bookmyshow.com/movies/buytickets/ET87654321/20260720",
            "date_str": "20260720",
            "theatres": ["PVR Phoenix"]
        },
        notification_medium="SMS",
        notification_config={"phone_number": "+919876543210"},
        created_by="user-cancelling"
    )
    job.status = "Cancelling"
    manager.jobs[job_id] = job
    manager._save_job_to_firestore(job)

    claimed = manager.claim_notification_slot(job)
    assert claimed is False

    # Also test when status is Stopped
    job.status = "Stopped"
    manager._save_job_to_firestore(job)
    claimed2 = manager.claim_notification_slot(job)
    assert claimed2 is False

    # Clean up
    if job_id in manager.jobs:
        del manager.jobs[job_id]
