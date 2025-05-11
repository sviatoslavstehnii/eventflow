from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field

class NotificationBase(BaseModel):
    user_id: str
    type: str
    content: str
    status: str = "pending"

class NotificationCreate(NotificationBase):
    pass

class Notification(NotificationBase):
    id: str
    created_at: datetime
    sent_at: Optional[datetime] = None

    class Config:
        from_attributes = True

class NotificationUpdate(BaseModel):
    status: Optional[str] = None
    sent_at: Optional[datetime] = None

class NotificationTemplate(BaseModel):
    type: str
    subject: str
    body: str
    variables: list[str] 