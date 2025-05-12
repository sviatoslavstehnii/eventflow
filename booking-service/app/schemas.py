from datetime import datetime
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field
from enum import Enum

class BookingStatus(str, Enum):
    CONFIRMED = "confirmed"
    CANCELLED = "cancelled"

class BookingBase(BaseModel):
    event_id: str

class BookingCreate(BookingBase):
    pass

class Booking(BookingBase):
    id: str
    user_id: str
    status: BookingStatus = BookingStatus.CONFIRMED
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

class BookingResponse(BaseModel):
    id: str
    event_id: str
    user_id: str
    status: BookingStatus
    created_at: datetime
    updated_at: datetime
    event_details: Optional[Dict[str, Any]] = None

    class Config:
        orm_mode = True