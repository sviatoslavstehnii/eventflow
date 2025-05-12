from motor.motor_asyncio import AsyncIOMotorDatabase
from . import models, schemas
from datetime import datetime
from bson import ObjectId

async def get_event(db: AsyncIOMotorDatabase, event_id: str):
    return await db.events.find_one({"_id": ObjectId(event_id)})

async def get_events(
    db: AsyncIOMotorDatabase,
    skip: int = 0,
    limit: int = 100,
    organizer_id: str = None,
    is_active: bool = None
):
    query = {}
    if organizer_id:
        query["organizer_id"] = organizer_id
    if is_active is not None:
        query["is_active"] = is_active
    
    cursor = db.events.find(query).skip(skip).limit(limit)
    return await cursor.to_list(length=limit)

async def create_event(db: AsyncIOMotorDatabase, event: schemas.EventCreate, organizer_id: str):
    event_dict = event.dict()
    event_dict["organizer_id"] = organizer_id
    event_dict["is_active"] = True
    event_dict["created_at"] = datetime.utcnow()
    event_dict["updated_at"] = datetime.utcnow()
    
    result = await db.events.insert_one(event_dict)
    event_dict["_id"] = result.inserted_id
    return event_dict

async def update_event(db: AsyncIOMotorDatabase, event_id: str, event: schemas.EventUpdate):
    update_data = event.dict(exclude_unset=True)
    if update_data:
        update_data["updated_at"] = datetime.utcnow()
        await db.events.update_one(
            {"_id": ObjectId(event_id)},
            {"$set": update_data}
        )
    
    return await get_event(db, event_id)

async def delete_event(db: AsyncIOMotorDatabase, event_id: str):
    result = await db.events.delete_one({"_id": ObjectId(event_id)})
    return result.deleted_count > 0
