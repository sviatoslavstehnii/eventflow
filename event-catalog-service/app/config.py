from pydantic_settings import BaseSettings
from functools import lru_cache
import os

class Settings(BaseSettings):
    JWT_SECRET: str = "your-secret-key"
    JWT_ALGORITHM: str = "HS256"
    AUTH_SERVICE_URL: str = "http://auth-service:8000"
    BOOKING_SERVICE_URL: str = "http://booking-service:8002"
    MONGODB_URL: str = os.getenv("MONGO_DETAILS", "mongodb://mongo_event:27017/eventcatalogdb")

    class Config:
        env_file = ".env"

@lru_cache()
def get_settings():
    return Settings()

settings = get_settings()