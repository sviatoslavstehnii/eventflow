import os
from dotenv import load_dotenv
import logging
import pika
import json
from datetime import datetime

load_dotenv()

RABBITMQ_HOST = os.getenv("RABBITMQ_HOST", "rabbitmq")
RABBITMQ_PORT = os.getenv("RABBITMQ_PORT", "5672")
RABBITMQ_USER = os.getenv("RABBITMQ_USER", "guest")
RABBITMQ_PASS = os.getenv("RABBITMQ_PASS", "guest")

async def send_booking_notification(
    user_email: str,
    user_full_name: str,
    event_title: str,
    booking_id: str,
    booking_status: str
):
    """
    Send a structured notification directly to the message queue.
    """
    message_for_mq = {
        "user_id": user_email,
        "user_email": user_email,
        "type": f"booking_{booking_status}",
        "content": f"Dear {user_full_name or 'Valued Customer'}, your booking for event '{event_title}' (Booking ID: {booking_id}) has been {booking_status}.",
        "status": "PENDING",
        "created_at": datetime.utcnow().isoformat()
    }

    try:
        mq_url = f"amqp://{RABBITMQ_USER}:{RABBITMQ_PASS}@{RABBITMQ_HOST}:{RABBITMQ_PORT}/"
        logging.info(f"Attempting to send notification for booking {booking_id} to RabbitMQ at {mq_url}")
        params = pika.URLParameters(mq_url)
        connection = pika.BlockingConnection(params)
        channel = connection.channel()
      
        channel.queue_declare(queue="notifications", durable=True)

        channel.basic_publish(
            exchange="",
            routing_key="notifications",
            body=json.dumps(message_for_mq),
            properties=pika.BasicProperties(
                delivery_mode=2,
            )
        )
        connection.close()
        logging.info(f"Successfully sent booking_{booking_status} notification for booking {booking_id} (User: {user_email}) to message queue.")
        return True
    except Exception as e:
        logging.error(f"Failed to send notification for booking {booking_id} to message queue: {e}")
        return False