import httpx
import logging
from .consul_client import ConsulClient

logging.basicConfig(level=logging.INFO)
consul_client = ConsulClient()

async def get_event_details(event_id: str):
    """Get event details from Event Catalog Service using service discovery"""
    event_service = consul_client.get_service("event-catalog-service")
    if not event_service:
        logging.error("Event Catalog service is not available")
        return None
    
    event_url = f"http://{event_service['host']}:{event_service['port']}/events/{event_id}"
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(event_url)
            if response.status_code == 200:
                return response.json()
            logging.error(f"Failed to get event details: {response.status_code}")
            return None
        except httpx.RequestError as e:
            logging.error(f"Could not connect to Event Catalog service: {str(e)}")
            return None
        
async def book_event(event_id: str, user_id: str):
    event_service = consul_client.get_service("event-catalog-service")
    if not event_service:
        raise Exception("Event Catalog Service not available")
    
    url = f"http://{event_service['host']}:{event_service['port']}/events/{event_id}/book"
    headers = {"Authorization": f"Bearer {user_id}"}
    
    async with httpx.AsyncClient() as client:
        response = await client.post(url, headers=headers)
        if response.status_code == 200:
            return True
        return False

async def update_event_capacity(event_id: str, decrement: bool = True):
    """Atomically update event capacity in Event Catalog Service"""
    event_service = consul_client.get_service("event-catalog-service")
    if not event_service:
        logging.error("Event Catalog service is not available")
        return None
    
    event_url = f"http://{event_service['host']}:{event_service['port']}/events/{event_id}/capacity"
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.put(
                event_url,
                json={"decrement": decrement}
            )
            if response.status_code == 200:
                return response.json()
            logging.error(f"Failed to update event capacity: {response.status_code}")
            return None
        except httpx.RequestError as e:
            logging.error(f"Could not connect to Event Catalog service: {str(e)}")
            return None
