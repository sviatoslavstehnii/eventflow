from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field
from bson import ObjectId

class PyObjectId(ObjectId):
    @classmethod
    def __get_validators__(cls):
        yield cls.validate

    @classmethod
    def validate(cls, v):
        if not ObjectId.is_valid(v):
            raise ValueError("Invalid ObjectId")
        return ObjectId(v)
    
    @classmethod
    def __get_pydantic_json_schema__(cls, core_schema, handler):
        """
        Provide JSON schema for this custom type in Pydantic v2.
        """
        string_schema = handler(str)
        string_schema.update(type="string")
        return string_schema

    @classmethod
    def __modify_schema__(cls, field_schema):
        field_schema.update(type="string")

class NotificationModel(BaseModel):
    id: PyObjectId = Field(default_factory=PyObjectId, alias="_id")
    user_id: str
    type: str
    content: str
    status: str = "pending"
    created_at: datetime = Field(default_factory=datetime.utcnow)
    sent_at: Optional[datetime] = None

    class Config:
        allow_population_by_field_name = True
        arbitrary_types_allowed = True
        json_encoders = {ObjectId: str}
        schema_extra = {
            "example": {
                "user_id": "user123",
                "type": "booking_confirmation",
                "content": "Your booking for Event XYZ has been confirmed",
                "status": "pending"
            }
        } 