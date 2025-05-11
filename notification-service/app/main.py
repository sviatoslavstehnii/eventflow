from fastapi import FastAPI, Depends, HTTPException, BackgroundTasks
from typing import List
from datetime import datetime
import pika
import json
from motor.motor_asyncio import AsyncIOMotorClient
from fastapi.middleware.cors import CORSMiddleware
import logging
import asyncio

from . import models, schemas, crud
from .database import get_database
from .notification_processor import process_notification
from .consul_client import ConsulClient

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Notification Service")

# Initialize Consul client
consul_client = ConsulClient()

# Register service with Consul on startup
@app.on_event("startup")
async def startup_event():
    try:
        consul_client.register_service()
        logger.info("Service registered with Consul")
    except Exception as e:
        logger.error(f"Failed to register service with Consul: {str(e)}")

    # Set up RabbitMQ connection and channel
    connection = pika.BlockingConnection(
        pika.ConnectionParameters(host='rabbitmq')
    )
    channel = connection.channel()
    
    # Declare the queue
    channel.queue_declare(queue='notifications')
    
    # Set up consumer
    def callback(ch, method, properties, body):
        notification_data = json.loads(body)
        # Run the async notification processor in the event loop
        asyncio.run(process_notification(notification_data))
    
    channel.basic_consume(
        queue='notifications',
        on_message_callback=callback,
        auto_ack=True
    )
    
    # Start consuming in a separate thread
    import threading
    thread = threading.Thread(target=channel.start_consuming)
    thread.daemon = True
    thread.start()

# Deregister service from Consul on shutdown
@app.on_event("shutdown")
async def shutdown_event():
    try:
        consul_client.deregister_service()
        logger.info("Service deregistered from Consul")
    except Exception as e:
        logger.error(f"Failed to deregister service from Consul: {str(e)}")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace with specific origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health")
async def health_check():
    """Health check endpoint for Consul"""
    return {"status": "healthy"}

@app.get("/notifications/{user_id}", response_model=List[schemas.Notification])
async def get_user_notifications(
    user_id: str,
    db: AsyncIOMotorClient = Depends(get_database)
):
    cursor = db.notifications.find({"user_id": user_id})
    notifications = await cursor.to_list(length=100)
    return notifications

@app.get("/notifications/status/{notification_id}", response_model=schemas.Notification)
async def get_notification_status(
    notification_id: str,
    db: AsyncIOMotorClient = Depends(get_database)
):
    notification = await db.notifications.find_one({"_id": notification_id})
    if not notification:
        raise HTTPException(status_code=404, detail="Notification not found")
    return notification

@app.post("/notifications/send", response_model=schemas.Notification)
async def send_notification(
    notification: schemas.NotificationCreate,
    background_tasks: BackgroundTasks,
    db: AsyncIOMotorClient = Depends(get_database)
):
    notification_dict = notification.dict()
    notification_dict["created_at"] = datetime.utcnow()
    
    # Store notification in MongoDB
    result = await db.notifications.insert_one(notification_dict)
    notification_dict["id"] = str(result.inserted_id)
    
    # Send to RabbitMQ for processing
    connection = pika.BlockingConnection(
        pika.ConnectionParameters(host='rabbitmq')
    )
    channel = connection.channel()
    
    channel.basic_publish(
        exchange='',
        routing_key='notifications',
        body=json.dumps(notification_dict)
    )
    
    connection.close()
    
    return notification_dict 