from pydantic import BaseModel
from datetime import datetime
from typing import Optional

class NotificationModel(BaseModel):
    user_id: str
    type: str
    content: str
    status: str = "pending"
    created_at: datetime
    sent_at: Optional[datetime] = None