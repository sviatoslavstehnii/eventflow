from datetime import datetime
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field
from enum import Enum
import uuid

class BookingStatus(str, Enum):
    CONFIRMED = "confirmed"
    CANCELLED = "cancelled"

class BookingBase(BaseModel):
    event_id: str

class BookingCreate(BookingBase):
    pass

class Booking(BaseModel):
    id: str
    user_id: str
    event_id: str
    status: BookingStatus = BookingStatus.CONFIRMED
    created_at: datetime
    updated_at: datetime

    @classmethod
    def validate(cls, value):
        # Convert ObjectId to str if needed
        if isinstance(value, dict) and "id" in value and not isinstance(value["id"], str):
            value["id"] = str(value["id"])
        if isinstance(value, dict) and "event_id" in value and not isinstance(value["event_id"], str):
            value["event_id"] = str(value["event_id"])
        return value

    class Config:
        from_attributes = True
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

    @classmethod
    def validate(cls, value):
        if isinstance(value, dict) and "id" in value and not isinstance(value["id"], str):
            value["id"] = str(value["id"])
        if isinstance(value, dict) and "event_id" in value and not isinstance(value["event_id"], str):
            value["event_id"] = str(value["event_id"])
        return value

    class Config:
        from_attributes = True # Changed from orm_mode for Pydantic v2

class BookingCreateInternal(BookingBase):
    user_id: str # User ID is provided directly