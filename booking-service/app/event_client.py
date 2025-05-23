import httpx
import logging
from .consul_client import ConsulClient

logging.basicConfig(level=logging.INFO)
consul_client = ConsulClient()

async def get_event_details(event_id: str):
    """Get event details (just to read capacity)."""
    service = consul_client.get_service("event-catalog-service")
    if not service:
        logging.error("Event Catalog service unavailable")
        return None

    url = f"http://{service['host']}:{service['port']}/events/{event_id}"
    async with httpx.AsyncClient() as client:
        try:
            r = await client.get(url)
            if r.status_code == 200:
                return r.json()
            logging.error(f"GET /events/{event_id} → {r.status_code}")
        except httpx.RequestError as e:
            logging.error(f"Could not reach Event Catalog: {e}")
    return None

async def book_event(event_id: str, jwt_token: str) -> bool:
    """
    Ask the Event Catalog Service to atomically book a seat.
    Pass the user's JWT in the Authorization header so the
    /events/{id}/book endpoint can authenticate & authorize.
    """
    event_service = consul_client.get_service("event-catalog-service")
    if not event_service:
        logging.error("Event Catalog Service not available")
        return False

    url = f"http://{event_service['host']}:{event_service['port']}/events/{event_id}/book"
    headers = {"Authorization": f"Bearer {jwt_token}"}

    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(url, headers=headers)
            payload = response.json()
            if response.status_code == 200:
                logging.info(f"Success: {payload.get('message')}")
            else:
                logging.info(f"Failed: {payload.get('message')}")

            return response.status_code == 200
        except httpx.RequestError as e:
            logging.error(f"Failed to call book endpoint: {str(e)}")
            return False


async def update_event_capacity_in_catalog(event_id: str, increment: bool = True):
    """Calls the Event Catalog Service to update event capacity."""
    event_catalog_service = consul_client.get_service("event-catalog-service")
    if not event_catalog_service:
        logging.error("Event Catalog service is not available for capacity update.")
        return False # Indicate failure
    
    service_host = event_catalog_service['host']
    service_port = event_catalog_service['port']
    capacity_url = f"http://{service_host}:{service_port}/events/{event_id}/capacity"
    
    async with httpx.AsyncClient() as client:
        try:
            payload = {"increment": increment}
            response = await client.put(capacity_url, json=payload)
            
            if response.status_code == 200:
                logging.info(f"Successfully updated capacity for event {event_id} (increment: {increment}). Response: {response.json()}")
                return True # Indicate success
            else:
                logging.error(f"Failed to update capacity for event {event_id}. Status: {response.status_code}, Response: {response.text}")
                return False # Indicate failure
        except httpx.RequestError as e:
            logging.error(f"Could not connect to Event Catalog service at {capacity_url} for capacity update: {str(e)}")
            return False # Indicate failure
