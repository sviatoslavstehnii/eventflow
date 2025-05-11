import httpx
import os
from dotenv import load_dotenv

load_dotenv()

NOTIFICATION_SERVICE_URL = os.getenv("NOTIFICATION_SERVICE_URL", "http://notification-service:8004")

async def send_booking_notification(user_id: str, event_id: str, notification_type: str):
    """
    Send a notification to the notification service
    """
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{NOTIFICATION_SERVICE_URL}/notifications/send",
                json={
                    "user_id": user_id,
                    "type": notification_type,
                    "content": f"Booking {notification_type} for event {event_id}",
                    "status": "pending"
                }
            )
            return response.status_code == 200
    except httpx.RequestError:
        # Log the error but don't fail the booking process
        print(f"Failed to send notification for booking {event_id}")
        return False 