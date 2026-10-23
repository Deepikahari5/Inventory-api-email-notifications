from sqlalchemy import select

from app.models.notification_log import NotificationLog
from app.repositories.base import BaseRepository


class NotificationLogRepository(BaseRepository[NotificationLog]):
    model = NotificationLog

    def recent(self, status: str | None = None, skip: int = 0, limit: int = 50) -> list[NotificationLog]:
        statement = select(NotificationLog)
        if status:
            statement = statement.where(NotificationLog.status == status)
        statement = statement.order_by(NotificationLog.id.desc()).offset(skip).limit(limit)
        return list(self.db.scalars(statement))
