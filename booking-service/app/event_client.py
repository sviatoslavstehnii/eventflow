import httpx
import logging
from .consul_client import ConsulClient

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize Consul client
consul_client = ConsulClient()

async def get_event_details(event_id: str):
    """Get event details from Event Catalog Service using service discovery"""
    event_service = consul_client.get_service("event-catalog-service")
    if not event_service:
        logger.error("Event Catalog service is not available")
        return None
    
    event_url = f"http://{event_service['host']}:{event_service['port']}/events/{event_id}"
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(event_url)
            if response.status_code == 200:
                return response.json()
            logger.error(f"Failed to get event details: {response.status_code}")
            return None
        except httpx.RequestError as e:
            logger.error(f"Could not connect to Event Catalog service: {str(e)}")
            return None

async def update_event_capacity(event_id: str, increment: bool = True):
    """Update event capacity in Event Catalog Service using service discovery"""
    event_service = consul_client.get_service("event-catalog-service")
    if not event_service:
        logger.error("Event Catalog service is not available")
        return None
    
    event_url = f"http://{event_service['host']}:{event_service['port']}/events/{event_id}/capacity"
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.put(
                event_url,
                json={"increment": increment}
            )
            if response.status_code == 200:
                return response.json()
            logger.error(f"Failed to update event capacity: {response.status_code}")
            return None
        except httpx.RequestError as e:
            logger.error(f"Could not connect to Event Catalog service: {str(e)}")
            return None 