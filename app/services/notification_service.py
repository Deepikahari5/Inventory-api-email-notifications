from sqlalchemy.orm import Session

from app.models.notification_log import NotificationLog
from app.repositories.notification_repository import NotificationLogRepository


class NotificationService:
    def __init__(self, db: Session):
        self.logs = NotificationLogRepository(db)

    def recent(self, status: str | None, skip: int, limit: int) -> list[NotificationLog]:
        return self.logs.recent(status, skip, limit)
