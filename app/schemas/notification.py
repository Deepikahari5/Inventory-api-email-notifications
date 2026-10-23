from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr


class NotificationLogRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    notification_type: str
    recipient: str
    reference: str | None
    status: str
    error: str | None
    created_at: datetime


class TestEmailRequest(BaseModel):
    recipient: EmailStr | None = None
