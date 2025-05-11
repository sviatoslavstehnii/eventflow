import os
from motor.motor_asyncio import AsyncIOMotorClient
from fastapi import Depends

MONGODB_URL   = os.getenv("MONGODB_URL", "mongodb://notification-db:27017")
DATABASE_NAME = os.getenv("DATABASE_NAME", "notification_db")

_client = AsyncIOMotorClient(MONGODB_URL)
_db     = _client[DATABASE_NAME]

async def get_database():
    """
    FastAPI dependency that returns a Motor (async) MongoDB handle.
    """
    return _db
