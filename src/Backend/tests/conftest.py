# src/Backend/tests/conftest.py

import os
import sys

backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

os.environ["DISABLE_SECURITY"] = "true"
os.environ["DISABLE_PAYMENTS"] = "false"
os.environ["ENVIRONMENT"] = "development"
os.environ["NOTIFICATION_PROVIDER"] = "twilio"
os.environ["PAYMENT_GATEWAY"] = "cashfree"
os.environ["TWILIO_ACCOUNT_SID"] = "ACmockaccountsid0000000000000000"
os.environ["TWILIO_AUTH_TOKEN"] = "mockauthtoken00000000000000000"
os.environ["TWILIO_PHONE_NUMBER"] = "+919876543210"
os.environ["CASHFREE_APP_ID"] = "mock_cf_app_id"
os.environ["CASHFREE_SECRET_KEY"] = "mock_cf_secret_key"
os.environ["CASHFREE_WEBHOOK_SECRET"] = "mock_webhook_secret"

import pytest
import pytest_asyncio
from unittest.mock import MagicMock
from httpx import AsyncClient, ASGITransport

from main import app
from lib.core import auth

@pytest.fixture(autouse=True)
def mock_firebase_and_db(monkeypatch):
    """Mocks Firebase Authentication and Firestore client for all tests."""
    mock_db = MagicMock()
    storage = {}

    class MockDocRef:
        def __init__(self, col_name, doc_id):
            self.col_name = col_name
            self.id = doc_id
            self.path = f"{col_name}/{doc_id}"
            self.reference = self

        def _clean_data(self, data):
            import datetime
            from google.cloud.firestore_v1.transforms import Sentinel
            if not isinstance(data, dict):
                return data
            cleaned = {}
            for k, v in data.items():
                if isinstance(v, Sentinel) or "Sentinel" in type(v).__name__:
                    cleaned[k] = datetime.datetime.now(datetime.timezone.utc)
                elif isinstance(v, dict):
                    cleaned[k] = self._clean_data(v)
                else:
                    cleaned[k] = v
            return cleaned

        def get(self, transaction=None):
            snap = MagicMock()
            snap.exists = self.path in storage
            data = storage.get(self.path, {})
            snap.to_dict.return_value = self._clean_data(dict(data))
            snap.id = self.id
            snap.reference = self
            return snap

        def set(self, data, merge=False):
            cleaned = self._clean_data(dict(data))
            if merge and self.path in storage:
                storage[self.path].update(cleaned)
            else:
                storage[self.path] = cleaned

        def update(self, data):
            cleaned = self._clean_data(dict(data))
            if self.path not in storage:
                storage[self.path] = {}
            storage[self.path].update(cleaned)

        def delete(self):
            storage.pop(self.path, None)

    class MockCollectionRef:
        def __init__(self, col_name, filters=None):
            self.col_name = col_name
            self.filters = filters or []

        def document(self, doc_id=None):
            if not doc_id:
                import uuid
                doc_id = str(uuid.uuid4())
            return MockDocRef(self.col_name, doc_id)

        def where(self, field, op, val):
            new_filters = list(self.filters) + [(field, op, val)]
            return MockCollectionRef(self.col_name, filters=new_filters)

        def order_by(self, field, direction=None):
            return self

        def limit(self, count):
            return self

        def stream(self, transaction=None):
            matching = []
            prefix = f"{self.col_name}/"
            for p, d in list(storage.items()):
                if p.startswith(prefix):
                    match = True
                    for field, op, val in self.filters:
                        if op == "==" and d.get(field) != val:
                            match = False
                            break
                    if match:
                        doc_id = p.split("/", 1)[1]
                        ref = MockDocRef(self.col_name, doc_id)
                        matching.append(ref.get())
            return matching

    mock_db.collection.side_effect = lambda col: MockCollectionRef(col)

    class MockTransaction:
        _read_only = False
        _id = b"mock-txn-id"
        _max_attempts = 5

        def _clean_up(self):
            pass

        def _rollback(self):
            pass

        def _commit(self):
            pass

        def get(self, ref):
            return ref.get(transaction=self)

        def set(self, ref, data, merge=False):
            ref.set(data, merge=merge)

        def update(self, ref, data):
            ref.update(data)

        def delete(self, ref):
            ref.delete()

    mock_db.transaction.side_effect = lambda: MockTransaction()

    from google.cloud import firestore as real_firestore
    monkeypatch.setattr(real_firestore, "transactional", lambda fn: fn)

    class MockBatch:
        def __init__(self):
            self._ops = []

        def set(self, ref, data, merge=False):
            self._ops.append(("set", ref, data, merge))

        def update(self, ref, data):
            self._ops.append(("update", ref, data))

        def delete(self, ref):
            self._ops.append(("delete", ref))

        def commit(self):
            for op in self._ops:
                if op[0] == "set":
                    op[1].set(op[2], merge=op[3])
                elif op[0] == "update":
                    op[1].update(op[2])
                elif op[0] == "delete":
                    op[1].delete()

    mock_db.batch.side_effect = lambda: MockBatch()

    # Patch global db everywhere
    monkeypatch.setattr(auth, "db", mock_db)
    from lib.services import wallet, pricing, terms
    from lib.core import monitor
    monkeypatch.setattr(wallet, "db", mock_db)
    monkeypatch.setattr(pricing, "db", mock_db)
    monkeypatch.setattr(terms, "db", mock_db)
    from api.routers import jobs, wallet as wallet_r, payments, profile, consent, twilio_webhooks, cashfree_webhooks, admin
    monkeypatch.setattr(jobs, "db", mock_db)
    monkeypatch.setattr(wallet_r, "db", mock_db)
    monkeypatch.setattr(payments, "db", mock_db)
    monkeypatch.setattr(profile, "db", mock_db)
    monkeypatch.setattr(consent, "db", mock_db)
    monkeypatch.setattr(twilio_webhooks, "db", mock_db)
    monkeypatch.setattr(cashfree_webhooks, "db", mock_db)
    monkeypatch.setattr(admin, "db", mock_db)

    # Mock user details
    monkeypatch.setattr("api.dependencies.get_user_details", lambda uid=None, claims=None: ("Test User", "testuser@example.com", "https://photo.url"))

    storage["users/test-user-uid-123"] = {
        "uid": "test-user-uid-123",
        "email": "testuser@example.com",
        "terms_version_accepted": "2.0",
    }
    storage["users/test-admin-uid-999"] = {
        "uid": "test-admin-uid-999",
        "email": "admin@example.com",
        "terms_version_accepted": "2.0",
    }

    return mock_db

@pytest.fixture
def mock_user_claims():
    return {
        "uid": "test-user-uid-123",
        "email": "testuser@example.com",
        "authorized": True,
        "role": "user"
    }

@pytest.fixture
def mock_admin_claims():
    return {
        "uid": "test-admin-uid-999",
        "email": "admin@example.com",
        "authorized": True,
        "role": "admin"
    }

@pytest_asyncio.fixture
async def async_client(mock_user_claims):
    from lib.core.auth import get_authorized_user, get_current_user_claims
    app.dependency_overrides[get_authorized_user] = lambda: mock_user_claims
    app.dependency_overrides[get_current_user_claims] = lambda: mock_user_claims
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client
    app.dependency_overrides.clear()

@pytest_asyncio.fixture
async def admin_async_client(mock_admin_claims):
    from lib.core.auth import get_authorized_user, get_current_user_claims, get_admin_user
    app.dependency_overrides[get_authorized_user] = lambda: mock_admin_claims
    app.dependency_overrides[get_current_user_claims] = lambda: mock_admin_claims
    app.dependency_overrides[get_admin_user] = lambda: mock_admin_claims
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client
    app.dependency_overrides.clear()
