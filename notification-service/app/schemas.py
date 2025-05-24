from pydantic import BaseModel
from datetime import datetime
from typing import Optional
from enum import Enum

class NotificationType(str, Enum):
    BOOKING_CONFIRMED = "booking_confirmed"
    BOOKING_CANCELLED = "booking_cancelled"
    EVENT_UPDATED = "event_updated"

class NotificationStatus(str, Enum):
    PENDING = "pending"
    SENT = "sent"
    FAILED = "failed"

class NotificationCreate(BaseModel):
    user_id: str  #
    type: NotificationType
    content: str
    
class NotificationResponse(BaseModel):
    user_id: str
    type: NotificationType
    content: str
    status: NotificationStatus = NotificationStatus.PENDING
    created_at: datetime
    sent_at: Optional[datetime] = None
