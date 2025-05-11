from datetime import datetime
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field

class BookingBase(BaseModel):
    event_id: str
    status: str = "pending"

class BookingCreate(BookingBase):
    pass

class Booking(BookingBase):
    id: str
    user_id: str
    created_at: datetime
    updated_at: datetime

    class Config:
        json_schema_extra = {
            "example": {
                "id": "507f1f77bcf86cd799439011",
                "event_id": "507f1f77bcf86cd799439012",
                "user_id": "507f1f77bcf86cd799439013",
                "status": "confirmed",
                "created_at": "2024-02-20T10:00:00",
                "updated_at": "2024-02-20T10:00:00"
            }
        }

class BookingResponse(Booking):
    event_details: Optional[Dict[str, Any]] = None

class BookingUpdate(BaseModel):
    """Fields allowed for partial update on a booking."""
    status: Optional[str] = None