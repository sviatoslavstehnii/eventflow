from motor.motor_asyncio import AsyncIOMotorDatabase
from . import models, schemas
from datetime import datetime
from bson import ObjectId

async def get_event(db: AsyncIOMotorDatabase, event_id: str):
    # Convert event_id to ObjectId if possible
    query_id = event_id
    try:
        query_id = ObjectId(event_id)
    except Exception:
        pass
    event = await db.events.find_one({"_id": query_id})
    if event and "_id" in event and not isinstance(event["_id"], str):
        event["_id"] = str(event["_id"])
    return event

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
    events = await cursor.to_list(length=limit)
    # Convert all _id fields to str
    for ev in events:
        if "_id" in ev and not isinstance(ev["_id"], str):
            ev["_id"] = str(ev["_id"])
    return events

async def create_event(db: AsyncIOMotorDatabase, event: schemas.EventCreate, organizer_id: str):
    event_dict = event.dict()
    event_dict["organizer_id"] = organizer_id
    event_dict["is_active"] = True
    event_dict["created_at"] = datetime.utcnow()
    event_dict["updated_at"] = datetime.utcnow()
    result = await db.events.insert_one(event_dict)
    event_dict["_id"] = str(result.inserted_id)
    return event_dict

async def update_event(db: AsyncIOMotorDatabase, event_id: str, event: schemas.EventUpdate):
    update_data = event.dict(exclude_unset=True)
    if update_data:
        update_data["updated_at"] = datetime.utcnow()
        await db.events.update_one(
            {"_id": event_id},
            {"$set": update_data}
        )
    return await get_event(db, event_id)

async def delete_event(db: AsyncIOMotorDatabase, event_id: str):
    result = await db.events.delete_one({"_id": event_id})
    return result.deleted_count > 0

async def search_events(db: AsyncIOMotorDatabase, query: str):
    cursor = db.events.find({"title": {"$regex": query, "$options": "i"}})
    events = await cursor.to_list(length=100)
    for ev in events:
        if "_id" in ev and not isinstance(ev["_id"], str):
            ev["_id"] = str(ev["_id"])
    return events

async def update_event_capacity(db: AsyncIOMotorDatabase, event_id: str, increment: bool = True):
    # Convert event_id to ObjectId if possible
    query_id = event_id
    try:
        query_id = ObjectId(event_id)
    except Exception:
        pass
    result = await db.events.find_one_and_update(
        {"_id": query_id},
        {"$inc": {"capacity": 1 if increment else -1}},
        return_document=True
    )
    if result and "_id" in result and not isinstance(result["_id"], str):
        result["_id"] = str(result["_id"])
    return result
