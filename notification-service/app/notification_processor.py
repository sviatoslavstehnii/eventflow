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

async def process_notification(notification_data: dict):
    """Process a notification and send it to the appropriate channel"""
    try:
        notification_type = notification_data.get("type")
        user_id = notification_data.get("user_id")
        event_id = notification_data.get("event_id")
        
        if not all([notification_type, user_id, event_id]):
            logger.error("Missing required notification data")
            return
        
        # Get event details for the notification
        event = await get_event_details(event_id)
        if not event:
            logger.error(f"Could not get event details for event {event_id}")
            return
        
        # Process different notification types
        if notification_type == "booking_confirmed":
            logger.info(f"Sending booking confirmation to user {user_id} for event {event['title']}")
            # Add your notification sending logic here
            # For example, send email, push notification, etc.
            
        elif notification_type == "booking_cancelled":
            logger.info(f"Sending booking cancellation to user {user_id} for event {event['title']}")
            # Add your notification sending logic here
            
        elif notification_type == "event_updated":
            logger.info(f"Sending event update to user {user_id} for event {event['title']}")
            # Add your notification sending logic here
            
        else:
            logger.warning(f"Unknown notification type: {notification_type}")
            
    except Exception as e:
        logger.error(f"Error processing notification: {str(e)}") 