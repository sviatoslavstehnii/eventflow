from motor.motor_asyncio import AsyncIOMotorClient
from .config import settings

client = AsyncIOMotorClient(settings.MONGODB_URL)
db = client[settings.MONGODB_URL.split("/")[-1]]

async def get_database():
    try:
        yield db
    finally:
        pass