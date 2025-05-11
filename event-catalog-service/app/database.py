from motor.motor_asyncio import AsyncIOMotorClient
from .config import settings

client = AsyncIOMotorClient(settings.MONGODB_URL)
db = client.eventflow

async def get_database():
    try:
        yield db
    finally:
        pass  # Connection is managed by the client 