import smtplib

import pytest

from app.core.config import get_settings
from app.core.exceptions import EmailDeliveryError
from app.services.email_service import EmailService


def make_service(**overrides):
    return EmailService(get_settings().model_copy(update=overrides))


def test_smtp_errors_are_wrapped(monkeypatch):
    class BrokenSMTP:
        def __init__(self, *args, **kwargs):
            raise smtplib.SMTPConnectError(421, "unavailable")

    monkeypatch.setattr(smtplib, "SMTP", BrokenSMTP)
    with pytest.raises(EmailDeliveryError):
        make_service().send_email("user@example.com", "Hi", "Body")


def test_connection_errors_are_wrapped(monkeypatch):
    def refuse(*args, **kwargs):
        raise ConnectionRefusedError("refused")

    monkeypatch.setattr(smtplib, "SMTP", refuse)
    with pytest.raises(EmailDeliveryError):
        make_service().send_email("user@example.com", "Hi", "Body")


def test_missing_recipient_is_rejected():
    with pytest.raises(EmailDeliveryError):
        make_service().send_email("  ", "Hi", "Body")


def test_disabled_email_returns_false(monkeypatch):
    service = make_service(email_enabled=False)
    monkeypatch.setattr(service, "_deliver", lambda message: pytest.fail("should not deliver"))
    assert service.send_email("user@example.com", "Hi", "Body") is False


def test_smtp_flow_uses_tls_and_login(monkeypatch):
    calls = []

    class FakeSMTP:
        def __init__(self, host, port, timeout):
            calls.append(("connect", host, port, timeout))

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def starttls(self):
            calls.append(("starttls",))

        def login(self, username, password):
            calls.append(("login", username, password))

        def send_message(self, message):
            calls.append(("send", message["To"], message["Subject"]))

    monkeypatch.setattr(smtplib, "SMTP", FakeSMTP)
    service = make_service(
        smtp_host="smtp.test", smtp_port=587, smtp_username="user", smtp_password="pw", smtp_use_tls=True
    )
    assert service.send_email("to@example.com", "Line one\nLine two", "Body") is True
    assert calls[0][:3] == ("connect", "smtp.test", 587)
    assert ("starttls",) in calls
    assert ("login", "user", "pw") in calls
    assert calls[-1] == ("send", "to@example.com", "Line one Line two")


def test_low_stock_message_contents(monkeypatch):
    sent = []
    service = make_service()
    monkeypatch.setattr(service, "_deliver", lambda message: sent.append(message))
    service.send_low_stock_alert("Widget", "W-1", 2, 5)
    body = sent[0].get_content()
    assert "Widget" in body and "W-1" in body
    assert "Current stock quantity: 2" in body
    assert "Reorder level: 5" in body
