import logging
import smtplib
from email.message import EmailMessage

from app.core.config import Settings, get_settings
from app.core.exceptions import EmailDeliveryError

logger = logging.getLogger(__name__)


def _clean_header(value: str) -> str:
    return " ".join(value.split())


class EmailService:
    def __init__(self, settings: Settings | None = None):
        self._settings = settings or get_settings()

    def send_email(self, recipient: str, subject: str, body: str) -> bool:
        if not recipient or not recipient.strip():
            raise EmailDeliveryError("A recipient address is required")
        if not self._settings.email_enabled:
            logger.info("Email delivery disabled; skipping message to %s", recipient)
            return False
        message = EmailMessage()
        message["From"] = _clean_header(self._settings.email_sender)
        message["To"] = _clean_header(recipient)
        message["Subject"] = _clean_header(subject)
        message.set_content(body)
        self._deliver(message)
        return True

    def _deliver(self, message: EmailMessage) -> None:
        cfg = self._settings
        try:
            with smtplib.SMTP(cfg.smtp_host, cfg.smtp_port, timeout=cfg.smtp_timeout_seconds) as server:
                if cfg.smtp_use_tls:
                    server.starttls()
                if cfg.smtp_username:
                    server.login(cfg.smtp_username, cfg.smtp_password)
                server.send_message(message)
        except (smtplib.SMTPException, OSError) as exc:
            raise EmailDeliveryError(f"Failed to deliver email to {message['To']}: {exc}") from exc

    def send_to_user(self, email: str, subject: str, body: str) -> bool:
        return self.send_email(email, subject, body)

    def send_admin_alert(self, subject: str, body: str) -> bool:
        return self.send_email(self._settings.admin_notification_email, f"[Inventory Alert] {subject}", body)

    def send_registration_confirmation(self, username: str, email: str) -> bool:
        body = (
            f"Hello {username},\n\n"
            f"Your account on {self._settings.app_name} has been created successfully.\n"
            f"Username: {username}\n\n"
            "You can now sign in and start using the platform.\n"
            "If you did not create this account, please contact an administrator.\n"
        )
        return self.send_to_user(email, f"Welcome to {self._settings.app_name}", body)

    def send_low_stock_alert(self, product_name: str, sku: str, stock_quantity: int, reorder_level: int) -> bool:
        body = (
            "A product has reached its reorder level.\n\n"
            f"Product: {product_name}\n"
            f"SKU: {sku}\n"
            f"Current stock quantity: {stock_quantity}\n"
            f"Reorder level: {reorder_level}\n\n"
            "Please arrange a restock.\n"
        )
        return self.send_admin_alert(f"Low stock: {product_name}", body)

    def send_stock_notification(
        self,
        product_name: str,
        sku: str,
        operation: str,
        previous_quantity: int | None,
        new_quantity: int | None,
        performed_by: str,
        reason: str | None = None,
    ) -> bool:
        lines = [
            f"Operation: {operation}",
            f"Product: {product_name}",
            f"SKU: {sku}",
            f"Performed by: {performed_by}",
        ]
        if previous_quantity is not None:
            lines.append(f"Previous stock quantity: {previous_quantity}")
        if new_quantity is not None:
            lines.append(f"New stock quantity: {new_quantity}")
        if reason:
            lines.append(f"Reason: {reason}")
        return self.send_admin_alert(f"{operation}: {product_name}", "\n".join(lines) + "\n")


email_service = EmailService()
