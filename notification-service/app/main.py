from fastapi import FastAPI, Depends, HTTPException, BackgroundTasks
from typing import List
from datetime import datetime
import pika
import json
from motor.motor_asyncio import AsyncIOMotorClient

from . import models, schemas
from .database import get_database
from .notification_processor import process_notification

app = FastAPI(title="Notification Service")

@app.on_event("startup")
async def startup_event():
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
        process_notification(notification_data)
    
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