from fastapi import FastAPI, Depends, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from typing import List
from datetime import datetime
import redis
from cassandra.cluster import Cluster
import json
import uuid
import logging

from . import models, schemas
from .database import get_redis, get_cassandra
from .auth import get_current_user
from .notification import send_booking_notification
from .event_client import get_event_details, update_event_capacity, book_event
from .consul_client import ConsulClient

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Booking Service")

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
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health")
async def health_check():
    """Health check endpoint for Consul"""
    return {"status": "healthy"}

@app.post("/bookings", response_model=schemas.Booking)
async def create_booking(
    booking: schemas.BookingCreate,
    background_tasks: BackgroundTasks,
    current_user: dict = Depends(get_current_user),
    cassandra_session = Depends(get_cassandra)
):
    logger.info(f"Creating booking for event_id: {booking.event_id}")
    
    # Request the Event Catalog Service to book a seat
    booking_successful = await book_event(booking.event_id, current_user["id"])
    if not booking_successful:
        raise HTTPException(status_code=400, detail="Event is full")
    
    # Create booking in Cassandra
    booking_id = str(uuid.uuid4())
    booking_dict = {
        "id": booking_id,
        "event_id": booking.event_id,
        "user_id": current_user["id"],
        "status": "confirmed",
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow()
    }
    
    cassandra_session.execute(
        """
        INSERT INTO bookings (id, event_id, user_id, status, created_at, updated_at)
        VALUES (%s, %s, %s, %s, %s, %s)
        """,
        (
            booking_id,
            booking_dict["event_id"],
            booking_dict["user_id"],
            booking_dict["status"],
            booking_dict["created_at"],
            booking_dict["updated_at"]
        )
    )
    
    background_tasks.add_task(
        send_booking_notification,
        booking_dict["user_id"],
        booking_dict["event_id"],
        "booking_confirmed"
    )
    
    return booking_dict

@app.get("/bookings/user/{user_id}", response_model=List[schemas.BookingResponse])
async def get_user_bookings(
    user_id: str,
    current_user: dict = Depends(get_current_user),
    cassandra_session = Depends(get_cassandra)
):
    if user_id != current_user["id"]:
        raise HTTPException(status_code=403, detail="Not authorized to view these bookings")
    
    rows = cassandra_session.execute(
        "SELECT * FROM bookings WHERE user_id = %s",
        (user_id,)
    )
    
    bookings = []
    for row in rows:
        booking_dict = {
            "id": row.id,
            "event_id": row.event_id,
            "user_id": row.user_id,
            "status": row.status,
            "created_at": row.created_at,
            "updated_at": row.updated_at
        }
        
        # Get event details for each booking
        event_details = await get_event_details(booking_dict["event_id"])
        booking_dict["event_details"] = event_details
        bookings.append(booking_dict)
    
    return bookings

@app.get("/bookings/event/{event_id}", response_model=List[schemas.BookingResponse])
async def get_event_bookings(
    event_id: str,
    current_user: dict = Depends(get_current_user),
    cassandra_session = Depends(get_cassandra)
):
    # Verify if user is event organizer
    event = await get_event_details(event_id)
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    
    if event["organizer_id"] != current_user["id"]:
        raise HTTPException(status_code=403, detail="Not authorized to view these bookings")
    
    rows = cassandra_session.execute(
        "SELECT * FROM bookings WHERE event_id = %s",
        (event_id,)
    )
    
    bookings = []
    for row in rows:
        booking_dict = dict(row)
        booking_dict["event_details"] = event
        bookings.append(booking_dict)
    
    return bookings

@app.delete("/bookings/{booking_id}")
async def cancel_booking(
    booking_id: str,
    current_user: dict = Depends(get_current_user),
    redis_client: redis.Redis = Depends(get_redis),
    cassandra_session = Depends(get_cassandra)
):
    # Get booking details
    row = cassandra_session.execute(
        "SELECT * FROM bookings WHERE id = %s",
        (booking_id,)
    ).one()
    
    if not row:
        raise HTTPException(status_code=404, detail="Booking not found")
    
    booking = dict(row)
    if booking["user_id"] != current_user["id"]:
        raise HTTPException(status_code=403, detail="Not authorized to cancel this booking")
    
    # Update booking status
    cassandra_session.execute(
        """
        UPDATE bookings
        SET status = %s, updated_at = %s
        WHERE id = %s
        """,
        ("cancelled", datetime.utcnow(), booking_id)
    )
    
    event_key = f"event:{booking['event_id']}"
    event_data = redis_client.get(event_key)
    if event_data:
        event = json.loads(event_data)
        event["current_bookings"] -= 1
        redis_client.set(event_key, json.dumps(event))
    
    await update_event_capacity(booking["event_id"], increment=False)
    
    # Send cancellation notification
    await send_booking_notification(
        booking["user_id"],
        booking["event_id"],
        "booking_cancelled"
    )
    
    return {"message": "Booking cancelled successfully"} 