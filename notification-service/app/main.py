import os
from fastapi import FastAPI, BackgroundTasks, HTTPException
from pythonjsonlogger import jsonlogger
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
logger = logging.getLogger("notification-service")
handler = logging.StreamHandler()
fmt = jsonlogger.JsonFormatter(
    '%(asctime)s %(levelname)s %(name)s %(message)s %(pathname)s %(lineno)d'
)
handler.setFormatter(fmt)
logger.addHandler(handler)

consul_client = ConsulClient()
INTERNAL_API_KEY = os.getenv("INTERNAL_API_KEY", "super-secure-api-key")

async def verify_user_id(user_id: str) -> bool:
    logger.debug(f"Verifying user ID via Auth service: {user_id}")
    auth_service = consul_client.get_service("auth-service")
    if not auth_service:
        logger.error("Auth Service unavailable during user verification")
        raise HTTPException(status_code=503, detail="Auth Service unavailable")

    url = f"http://{auth_service['host']}:{auth_service['port']}/users/{user_id}"
    headers = {"X-Internal-API-Key": INTERNAL_API_KEY}
    logger.debug(f"Verification URL: {url}")

    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(url, headers=headers)
            logger.debug(f"Auth service response status: {response.status_code}")
            if response.status_code == 200:
                logger.info(f"User {user_id} verified successfully")
                return True
            logger.warning(f"User verification failed for {user_id}: status {response.status_code}")
            return False
        except httpx.RequestError as e:
            logger.error(f"Error connecting to Auth service: {str(e)}")
            raise HTTPException(status_code=503, detail="Auth Service unavailable")


@app.get("/health")
async def health_check():
    logger.info("Health check requested")
    return {"status": "healthy"}


@app.post("/notifications/send", response_model=NotificationResponse)
async def send_notification(
        notification: NotificationCreate,
        background_tasks: BackgroundTasks
):
    logger.info(f"Received send_notification request: user={notification.user_id}, type={notification.type}")
    # Verify the user ID before sending the notification
    if not await verify_user_id(notification.user_id):
        logger.warning(f"Invalid user ID, aborting notification: {notification.user_id}")
        raise HTTPException(status_code=400, detail="Invalid user ID")

    notification_data = {
        "user_id": notification.user_id,
        "type": notification.type,
        "content": notification.content,
        "status": NotificationStatus.PENDING,
        "created_at": datetime.utcnow().isoformat()
    }
    logger.info(f"Enqueuing notification for background processing: {notification_data}")
    background_tasks.add_task(process_notification, notification_data)
    return notification_data


def start_rabbitmq_consumer():
    try:
        connection = pika.BlockingConnection(pika.ConnectionParameters(host='rabbitmq'))
        channel = connection.channel()
        channel.queue_declare(queue="notifications", durable=True)
        logger.info("Connected to RabbitMQ and declared queue 'notifications'")
    except Exception as e:
        logger.error(f"Failed to connect to RabbitMQ: {str(e)}")
        return

    def callback(ch, method, properties, body):
        try:
            notification = json.loads(body)
            logger.info(f"Received message from RabbitMQ: {notification}")
            asyncio.run(process_notification(notification))
            logger.info("Processed notification and sending ACK")
            ch.basic_ack(delivery_tag=method.delivery_tag)
        except Exception as ex:
            logger.error(f"Error processing notification: {str(ex)}")

    channel.basic_consume(queue="notifications", on_message_callback=callback)
    logger.info("Starting RabbitMQ consuming loop")
    channel.start_consuming()


@app.on_event("startup")
async def startup_event():
    logger.info("Notification Service startup: launching RabbitMQ consumer thread")
    consumer_thread = threading.Thread(target=start_rabbitmq_consumer, daemon=True)
    consumer_thread.start()


@app.on_event("shutdown")
async def shutdown_event():
    logger.info("Notification Service is shutting down")
