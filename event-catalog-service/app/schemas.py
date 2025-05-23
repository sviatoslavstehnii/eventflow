from datetime import datetime
from typing import Optional, Any
from pydantic import BaseModel, Field



class EventBase(BaseModel):
    title: str
    description: str
    location: str
    start_time: datetime
    end_time: datetime
    capacity: int
    price: float

    model_config = {
        "json_schema_extra": {
            "example": {
                "title": "Tech Conference 2024",
                "description": "Annual technology conference",
                "start_time": "2024-06-01T09:00:00",
                "end_time": "2024-06-03T18:00:00",
                "location": "Convention Center",
                "capacity": 500,
                "price": 299.99
            }
        }
    }

class EventCreate(EventBase):
    pass

class EventUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    location: Optional[str] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    capacity: Optional[int] = None
    price: Optional[float] = None
    is_active: Optional[bool] = None

class EventCapacityUpdate(BaseModel):
    increment: bool = True

class Event(BaseModel):
    id: str = Field(default_factory=str, alias="_id")
    organizer_id: str
    is_active: bool
    created_at: datetime
    updated_at: Optional[datetime] = None


    model_config = {
        "populate_by_name": True,
        "arbitrary_types_allowed": True,
    }