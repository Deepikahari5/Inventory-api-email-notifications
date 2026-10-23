SECRET_PASSWORD = "Secret123!"


def register(client, username="alice", email="alice@example.com"):
    return client.post(
        "/auth/register",
        json={"username": username, "email": email, "password": SECRET_PASSWORD},
    )


def test_registration_sends_confirmation_email(client, outbox):
    response = register(client)
    assert response.status_code == 201
    assert len(outbox) == 1
    message = outbox[0]
    assert message["To"] == "alice@example.com"
    body = message.get_content()
    assert "alice" in body
    assert SECRET_PASSWORD not in body
    assert "hash" not in body.lower()
    assert "token" not in body.lower()


def test_duplicate_registration_sends_no_second_email(client, outbox):
    assert register(client).status_code == 201
    assert register(client).status_code == 409
    assert len(outbox) == 1


def test_email_failure_does_not_break_registration(client, failing_email, admin_headers):
    response = register(client)
    assert response.status_code == 201
    login = client.post("/auth/login", data={"username": "alice", "password": SECRET_PASSWORD})
    assert login.status_code == 200
    logs = client.get("/notifications/logs?status=failed", headers=admin_headers).json()
    assert len(logs) == 1
    assert logs[0]["notification_type"] == "registration"
    assert logs[0]["recipient"] == "alice@example.com"


def test_failed_registration_email_can_be_retried_without_duplicate_user(client, failing_email):
    assert register(client).status_code == 201
    assert register(client).status_code == 409


def test_notification_logs_require_admin(client, employee_headers):
    assert client.get("/notifications/logs", headers=employee_headers).status_code == 403


def test_admin_test_email_is_queued_and_sent(client, outbox, admin_headers):
    response = client.post("/notifications/test", headers=admin_headers)
    assert response.status_code == 202
    assert len(outbox) == 1
    assert outbox[0]["To"] == "admin@test.local"
