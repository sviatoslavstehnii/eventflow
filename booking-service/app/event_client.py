import httpx
import os
from dotenv import load_dotenv

load_dotenv()

EVENT_SERVICE_URL = os.getenv("EVENT_SERVICE_URL", "http://event-catalog-service:8002")

async def get_event_details(event_id: str):
    """
    Fetch event details from the event catalog service
    """
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{EVENT_SERVICE_URL}/events/{event_id}")
            if response.status_code == 200:
                return response.json()
            return None
    except httpx.RequestError:
        return None

async def update_event_capacity(event_id: str, increment: bool = True):
    """
    Update event capacity in the event catalog service
    """
    try:
        async with httpx.AsyncClient() as client:
            response = await client.put(
                f"{EVENT_SERVICE_URL}/events/{event_id}/capacity",
                json={"increment": increment}
            )
            return response.status_code == 200
    except httpx.RequestError:
        return False 