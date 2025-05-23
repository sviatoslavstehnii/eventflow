from datetime import datetime
from typing import Optional, Any
from pydantic import BaseModel, Field


class EventModel(BaseModel):
    id: str = Field(default_factory=str, alias="_id")
    title: str
    description: str
    location: str
    start_time: datetime
    end_time: datetime
    capacity: int
    price: float
    organizer_id: str
    is_active: bool = True
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


    model_config = {
        "populate_by_name": True,
        "arbitrary_types_allowed": True,
        "json_schema_extra": {
            "example": {
                "title": "Tech Conference 2024",
                "description": "Annual technology conference",
                "start_time": "2024-06-01T09:00:00",
                "end_time": "2024-06-03T18:00:00",
                "location": "Convention Center",
                "capacity": 500,
                "price": 299.99,
                "organizer_id": "user123"
            }
        }
    }