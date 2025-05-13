import os
from fastapi import FastAPI, BackgroundTasks, HTTPException
import httpx
import pika
import json
import logging
import threading
import asyncio
from .consul_client import ConsulClient
from .database import get_database
from .notification_processor import process_notification
from .schemas import NotificationCreate, NotificationResponse, NotificationType, NotificationStatus
from datetime import datetime

app = FastAPI()
logging.basicConfig(level=logging.INFO)
consul_client = ConsulClient()


INTERNAL_API_KEY = os.getenv("INTERNAL_API_KEY", "super-secure-api-key")

async def verify_user_id(user_id: str) -> bool:
    """
    Verifies that the user ID exists by calling the Auth Service.
    """
    auth_service = consul_client.get_service("auth-service")
    if not auth_service:
        raise HTTPException(status_code=503, detail="Auth Service unavailable")

    url = f"http://{auth_service['host']}:{auth_service['port']}/users/{user_id}"
    headers = {"X-Internal-API-Key": INTERNAL_API_KEY}
    
    async with httpx.AsyncClient() as client:
        response = await client.get(url, headers=headers)
        if response.status_code == 200:
            user_data = response.json()
            global user_email
            user_email = user_data.get("email")
            logging.info(f"User ID {user_id} verified with email {user_email}")
            return True
        return False

@app.get("/health")
async def health_check():
    return {"status": "healthy"}

@app.post("/notifications/send", response_model=NotificationResponse)
async def send_notification(
    notification: NotificationCreate, 
    background_tasks: BackgroundTasks
):
    # Verify the user ID before sending the notification
    if not await verify_user_id(notification.user_id):
        raise HTTPException(status_code=400, detail="Invalid user ID")

    notification_data = {
        "user_email": user_email,
        "user_id": notification.user_id,
        "type": notification.type,
        "content": notification.content,
        "status": NotificationStatus.PENDING,
        "created_at": datetime.utcnow()
    }
    
    background_tasks.add_task(process_notification, notification_data)
    return notification_data

def start_rabbitmq_consumer():
    connection = pika.BlockingConnection(pika.ConnectionParameters(host='rabbitmq'))
    channel = connection.channel()
    channel.queue_declare(queue="notifications", durable=True)
    logging.info("Connected to RabbitMQ")

    def callback(ch, method, properties, body):
        notification = json.loads(body)
        asyncio.run(process_notification(notification))
        ch.basic_ack(delivery_tag=method.delivery_tag)

    channel.basic_consume(queue="notifications", on_message_callback=callback)
    logging.info("Notification Service is now consuming notifications...")
    channel.start_consuming()

@app.on_event("startup")
async def startup_event():
    # Run the RabbitMQ consumer in a separate thread
    consumer_thread = threading.Thread(target=start_rabbitmq_consumer, daemon=True)
    consumer_thread.start()
    logging.info("RabbitMQ consumer thread started")

@app.on_event("shutdown")
async def shutdown_event():
    logging.info("Notification Service is shutting down")
