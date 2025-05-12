from fastapi import FastAPI, Depends, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordBearer
from typing import List
from datetime import datetime
import redis
import uuid
import logging

from . import schemas
from .database import get_redis, get_cassandra
from .auth import get_current_user, oauth2_scheme
from .notification import send_booking_notification
from .event_client import get_event_details
from .consul_client import ConsulClient

app = FastAPI(title="Booking Service")
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

consul_client = ConsulClient()

@app.on_event("startup")
async def startup_event():
    try:
        consul_client.register_service()
        logger.info("Booking Service registered with Consul")
    except Exception as e:
        logger.error(f"Failed to register Booking Service: {e}")

@app.on_event("shutdown")
async def shutdown_event():
    try:
        consul_client.deregister_service()
        logger.info("Booking Service deregistered from Consul")
    except Exception as e:
        logger.error(f"Failed to deregister Booking Service: {e}")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health")
async def health_check():
    return {"status": "healthy"}

@app.post("/bookings", response_model=schemas.Booking)
async def create_booking(
    booking: schemas.BookingCreate,
    background_tasks: BackgroundTasks,
    current_user: dict = Depends(get_current_user),
    token: str = Depends(oauth2_scheme),
    redis_client: redis.Redis = Depends(get_redis),
    cassandra_session = Depends(get_cassandra)
):
    logger.info(f"Creating booking for event_id={booking.event_id}")

    # 1) Fetch event to read its capacity
    event = await get_event_details(booking.event_id)
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")

    # 2) Compute or retrieve current booking count from Redis
    key = f"booking_count:{booking.event_id}"
    raw = redis_client.get(key)
    if raw is None:
        row = cassandra_session.execute(
            "SELECT COUNT(*) AS cnt FROM bookings WHERE event_id = %s AND status = %s ALLOW FILTERING",
            (booking.event_id, schemas.BookingStatus.CONFIRMED.value)
        ).one()
        current = row.cnt if row and hasattr(row, "cnt") else 0
        redis_client.set(key, current)
    else:
        current = int(raw)

    # 3) Check against event capacity
    if current >= event["capacity"]:
        raise HTTPException(status_code=400, detail="Event is full")

    # 4) Insert new booking
    booking_id = str(uuid.uuid4())
    new = {
        "id": booking_id,
        "event_id": booking.event_id,
        "user_id": current_user["id"],
        "status": schemas.BookingStatus.CONFIRMED,
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow()
    }
    cassandra_session.execute(
        """
        INSERT INTO bookings (id, event_id, user_id, status, created_at, updated_at)
        VALUES (%s, %s, %s, %s, %s, %s)
        """,
        (
            new["id"],
            new["event_id"],
            new["user_id"],
            new["status"].value,
            new["created_at"],
            new["updated_at"]
        )
    )

    # 5) Increment our local counter
    redis_client.incr(key)

    # 6) Send confirmation notification
    background_tasks.add_task(
        send_booking_notification,
        new["user_id"],
        new["event_id"],
        "booking_confirmed"
    )

    return new

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

    result = []
    for row in rows:
        booking = {
            "id": row.id,
            "event_id": row.event_id,
            "user_id": row.user_id,
            "status": row.status,
            "created_at": row.created_at,
            "updated_at": row.updated_at
        }
        booking["event_details"] = await get_event_details(row.event_id)
        result.append(booking)

    return result

@app.get("/bookings/event/{event_id}", response_model=List[schemas.BookingResponse])
async def get_event_bookings(
    event_id: str,
    current_user: dict = Depends(get_current_user),
    cassandra_session = Depends(get_cassandra)
):
    event = await get_event_details(event_id)
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    if event["organizer_id"] != current_user["id"]:
        raise HTTPException(status_code=403, detail="Not authorized to view these bookings")

    rows = cassandra_session.execute(
        "SELECT * FROM bookings WHERE event_id = %s",
        (event_id,)
    )

    result = []
    for row in rows:
        booking = {
            "id": row.id,
            "event_id": row.event_id,
            "user_id": row.user_id,
            "status": row.status,
            "created_at": row.created_at,
            "updated_at": row.updated_at,
            "event_details": event
        }
        result.append(booking)

    return result

@app.delete("/bookings/{booking_id}")
async def cancel_booking(
    booking_id: str,
    background_tasks: BackgroundTasks,
    current_user: dict          = Depends(get_current_user),
    redis_client: redis.Redis   = Depends(get_redis),
    cassandra_session           = Depends(get_cassandra),
):
    # 1) Fetch existing booking
    row = cassandra_session.execute(
        "SELECT event_id, user_id FROM bookings WHERE id = %s",
        (booking_id,)
    ).one()
    if not row:
        raise HTTPException(status_code=404, detail="Booking not found")

    # 2) Authorization
    if row.user_id != current_user["id"]:
        raise HTTPException(status_code=403, detail="Not authorized to delete this booking")

    # 3) Delete from Cassandra
    cassandra_session.execute(
        "DELETE FROM bookings WHERE id = %s",
        (booking_id,)
    )

    # 4) Decrement our Redis counter
    key = f"booking_count:{row.event_id}"
    redis_client.decr(key)

    # 5) (Optional) Notify user
    background_tasks.add_task(
        send_booking_notification,
        row.user_id,
        row.event_id,
        "booking_cancelled"
    )

    return {"message": "Booking deleted successfully"}
