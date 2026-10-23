import logging
from contextlib import contextmanager
from typing import Callable

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.database import SessionLocal
from app.core.exceptions import EmailDeliveryError
from app.models.notification_log import NotificationLog
from app.models.product import Product
from app.services.email_service import email_service
from app.services.product_service import InventoryEvent

logger = logging.getLogger(__name__)


@contextmanager
def task_session():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def _dispatch(
    db: Session,
    notification_type: str,
    recipient: str,
    reference: str | None,
    send: Callable[[], bool],
) -> str:
    status = "sent"
    error = None
    try:
        if not send():
            status = "skipped"
    except EmailDeliveryError as exc:
        status = "failed"
        error = str(exc)[:500]
        logger.error("Email task %s failed: %s", notification_type, exc)
    except Exception as exc:
        status = "failed"
        error = f"Unexpected error: {exc}"[:500]
        logger.exception("Unexpected error in email task %s", notification_type)
    db.add(
        NotificationLog(
            notification_type=notification_type,
            recipient=recipient,
            reference=reference,
            status=status,
            error=error,
        )
    )
    return status


def send_registration_email_task(user_id: int, username: str, email: str) -> None:
    try:
        with task_session() as db:
            _dispatch(
                db,
                "registration",
                email,
                f"user:{user_id}",
                lambda: email_service.send_registration_confirmation(username, email),
            )
            db.commit()
    except Exception:
        logger.exception("Registration email task crashed")


def send_low_stock_alert_task(product_id: int) -> None:
    try:
        with task_session() as db:
            product = db.get(Product, product_id)
            if product is None or product.stock_quantity > product.reorder_level:
                return
            name, sku = product.name, product.sku
            quantity, reorder = product.stock_quantity, product.reorder_level
            status = _dispatch(
                db,
                "low_stock",
                get_settings().admin_notification_email,
                f"product:{product_id}",
                lambda: email_service.send_low_stock_alert(name, sku, quantity, reorder),
            )
            if status == "failed":
                product.low_stock_notified = False
            db.commit()
    except Exception:
        logger.exception("Low stock alert task crashed")


def send_inventory_event_task(event: InventoryEvent, performed_by: str) -> None:
    try:
        with task_session() as db:
            _dispatch(
                db,
                "inventory_event",
                get_settings().admin_notification_email,
                f"sku:{event.sku}",
                lambda: email_service.send_stock_notification(
                    event.product_name,
                    event.sku,
                    event.operation,
                    event.previous_quantity,
                    event.new_quantity,
                    performed_by,
                    event.reason,
                ),
            )
            db.commit()
    except Exception:
        logger.exception("Inventory event task crashed")


def send_test_email_task(recipient: str, requested_by: str) -> None:
    try:
        with task_session() as db:
            _dispatch(
                db,
                "test_email",
                recipient,
                f"user:{requested_by}",
                lambda: email_service.send_to_user(
                    recipient,
                    "Inventory API test email",
                    "This is a test email from the Inventory Management API.\n",
                ),
            )
            db.commit()
    except Exception:
        logger.exception("Test email task crashed")
