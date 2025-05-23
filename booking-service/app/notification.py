import httpx
import os
from dotenv import load_dotenv

load_dotenv()

NOTIFICATION_SERVICE_URL = os.getenv("NOTIFICATION_SERVICE_URL", "http://notification-service:8003") 

async def send_booking_notification(
    user_email: str, 
    user_full_name: str,
    event_title: str,
    booking_id: str, 
    booking_status: str 
):
    """
    Send a structured notification to the notification service.
    """
    notification_payload = {
        "recipient_email": user_email,
        "recipient_name": user_full_name or "Valued Customer",
        "type": f"booking_{booking_status}", 
        "data": {
            "event_title": event_title,
            "booking_id": str(booking_id),
            "status": booking_status,
            
        }
    }

    target_url = f"{NOTIFICATION_SERVICE_URL}/notifications/" 

    try:
        async with httpx.AsyncClient() as client:
            message_content = f"Your booking for '{event_title}' (ID: {str(booking_id)}) has been {booking_status}."
            if booking_status == "confirmed":
                subject = f"Booking Confirmed: {event_title}"
            elif booking_status == "cancelled":
                subject = f"Booking Cancelled: {event_title}"
            else:
                subject = "Booking Update"


            notification_service_payload = {
                "user_id": user_email, 
                "type": f"booking_{booking_status}",
                "message_content": message_content,

            }
            response = await client.post(
                f"{NOTIFICATION_SERVICE_URL}/notifications/send", 
                json=notification_service_payload
            )
            if response.status_code == 200 or response.status_code == 202: 
                logging.info(f"Successfully sent {booking_status} notification for booking {booking_id} to {user_email}")
                return True
            else:
                logging.error(f"Failed to send notification for booking {booking_id}. Status: {response.status_code}, Response: {response.text}")
                return False
    except httpx.RequestError as e:
        logging.error(f"Notification service request error for booking {booking_id}: {e}")
        return False