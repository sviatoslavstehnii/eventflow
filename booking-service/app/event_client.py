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

# async def book_event(event_id: str, jwt_token: str) -> bool:
#     """
#     Ask the Event Catalog Service to atomically book a seat.
#     Pass the user's JWT in the Authorization header so the
#     /events/{id}/book endpoint can authenticate & authorize.
#     """
#     event_service = consul_client.get_service("event-catalog-service")
#     if not event_service:
#         logging.error("Event Catalog Service not available")
#         return False

#     url = f"http://{event_service['host']}:{event_service['port']}/events/{event_id}/book"
#     headers = {"Authorization": f"Bearer {jwt_token}"}

#     async with httpx.AsyncClient() as client:
#         try:
#             response = await client.post(url, headers=headers)
#             payload = response.json()
#             if response.status_code == 200:
#                 logging.info(f"Success: {payload.get('message')}")
#             else:
#                 logging.info(f"Failed: {payload.get('message')}")

#             return response.status_code == 200
#         except httpx.RequestError as e:
#             logging.error(f"Failed to call book endpoint: {str(e)}")
#             return False


# async def update_event_capacity(event_id: str, decrement: bool = True):
#     """Atomically update event capacity in Event Catalog Service"""
#     event_service = consul_client.get_service("event-catalog-service")
#     if not event_service:
#         logging.error("Event Catalog service is not available")
#         return None
    
#     event_url = f"http://{event_service['host']}:{event_service['port']}/events/{event_id}/capacity"
    
#     async with httpx.AsyncClient() as client:
#         try:
#             response = await client.put(
#                 event_url,
#                 json={"decrement": decrement}
#             )
#             if response.status_code == 200:
#                 return response.json()
#             logging.error(f"Failed to update event capacity: {response.status_code}")
#             return None
#         except httpx.RequestError as e:
#             logging.error(f"Could not connect to Event Catalog service: {str(e)}")
#             return None
