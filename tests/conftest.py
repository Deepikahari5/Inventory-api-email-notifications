import os
import tempfile

_db_path = os.path.join(tempfile.gettempdir(), f"inventory_test_{os.getpid()}.db")
os.environ["DATABASE_URL"] = f"sqlite:///{_db_path}"
os.environ["SECRET_KEY"] = "test-secret-key-for-automated-tests-only"
os.environ["ADMIN_NOTIFICATION_EMAIL"] = "admin@test.local"
os.environ["EMAIL_SENDER"] = "noreply@test.local"
os.environ["EMAIL_ENABLED"] = "true"
os.environ["ADMIN_USERNAME"] = ""
os.environ["ADMIN_EMAIL"] = ""
os.environ["ADMIN_PASSWORD"] = ""

import pytest
from fastapi.testclient import TestClient

from app.core.database import Base, SessionLocal, engine
from app.core.exceptions import EmailDeliveryError
from app.core.security import hash_password
from app.main import app
from app.models.user import User
from app.services.email_service import email_service

PASSWORD = "Password123!"


@pytest.fixture(autouse=True)
def database():
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    yield
    Base.metadata.drop_all(engine)


@pytest.fixture
def client():
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def outbox(monkeypatch):
    messages = []
    monkeypatch.setattr(email_service, "_deliver", lambda message: messages.append(message))
    return messages


@pytest.fixture
def failing_email(monkeypatch):
    def boom(message):
        raise EmailDeliveryError("smtp unavailable")

    monkeypatch.setattr(email_service, "_deliver", boom)


def create_user(role: str, username: str) -> None:
    with SessionLocal() as db:
        db.add(
            User(
                username=username,
                email=f"{username}@test.local",
                hashed_password=hash_password(PASSWORD),
                role=role,
                is_active=True,
            )
        )
        db.commit()


def login_headers(client: TestClient, username: str) -> dict:
    response = client.post("/auth/login", data={"username": username, "password": PASSWORD})
    assert response.status_code == 200, response.text
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


@pytest.fixture
def admin_headers(client):
    create_user("admin", "admin_user")
    return login_headers(client, "admin_user")


@pytest.fixture
def employee_headers(client):
    create_user("employee", "employee_user")
    return login_headers(client, "employee_user")
