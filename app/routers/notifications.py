from fastapi import APIRouter, BackgroundTasks, Depends, Query, status

from app.background.tasks import send_test_email_task
from app.core.config import get_settings
from app.dependencies import get_notification_service, require_roles
from app.models.user import User, UserRole
from app.schemas.notification import NotificationLogRead, TestEmailRequest
from app.schemas.user import MessageResponse
from app.services.notification_service import NotificationService

router = APIRouter(prefix="/notifications", tags=["Notifications"])

admin_only = require_roles(UserRole.ADMIN)


@router.get("/logs", response_model=list[NotificationLogRead])
def list_logs(
    status_filter: str | None = Query(None, alias="status"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    service: NotificationService = Depends(get_notification_service),
    _: User = Depends(admin_only),
):
    return service.recent(status_filter, skip, limit)


@router.post("/test", response_model=MessageResponse, status_code=status.HTTP_202_ACCEPTED)
def send_test_email(
    background_tasks: BackgroundTasks,
    payload: TestEmailRequest | None = None,
    actor: User = Depends(admin_only),
):
    recipient = (payload.recipient if payload and payload.recipient else None) or get_settings().admin_notification_email
    background_tasks.add_task(send_test_email_task, recipient, actor.username)
    return MessageResponse(message="Test email queued")
