from datetime import datetime
from typing import Optional, Any
from pydantic import BaseModel, Field
from bson import ObjectId
from uuid import UUID

class PyObjectId(ObjectId):
    @classmethod
    def __get_validators__(cls):
        yield cls.validate

    @classmethod
    def validate(cls, v: Any, handler: Any) -> ObjectId:
        if isinstance(v, ObjectId):
            return v
        if not ObjectId.is_valid(str(v)):
            raise ValueError("Invalid ObjectId")
        return ObjectId(str(v))

    @classmethod
    def __get_pydantic_json_schema__(cls, core_schema, handler):
        return {"type": "string"}

class BookingModel(BaseModel):
    id: str = Field(default_factory=str, alias="_id")
    event_id: str
    user_id: str
    status: str = "pending"
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: Optional[datetime] = None

    @classmethod
    def validate(cls, value):
        # Convert ObjectId to str if needed
        if isinstance(value, dict) and "_id" in value and not isinstance(value["_id"], str):
            value["_id"] = str(value["_id"])
        if isinstance(value, dict) and "event_id" in value and not isinstance(value["event_id"], str):
            value["event_id"] = str(value["event_id"])
        return value

    model_config = {
        "populate_by_name": True,
        "arbitrary_types_allowed": True,
        "json_schema_extra": {
            "example": {
                "event_id": "6820825288c75120f79deed4",
                "user_id": "840d016f-6692-4fd0-8f54-af82efd9e333",
                "status": "pending"
            }
        }
    }