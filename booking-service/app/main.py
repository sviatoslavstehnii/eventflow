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
from .event_client import get_event_details, update_event_capacity_in_catalog
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
    logger.info(f"Attempting to create booking for event_id={booking.event_id} by user_id={current_user['id']}")

    event = await get_event_details(booking.event_id)
    if not event:
        logger.warning(f"Event not found: {booking.event_id}")
        raise HTTPException(status_code=404, detail="Event not found")

    event_capacity = event.get("capacity")
    if event_capacity is None:
        logger.error(f"Event capacity not available for event_id={booking.event_id}")
        raise HTTPException(status_code=500, detail="Event capacity information is missing")

    key = f"booking_count:{booking.event_id}"
    current_booking_count = redis_client.incr(key)

    if current_booking_count > event_capacity:
        redis_client.decr(key)  # Rollback Redis increment
        logger.warning(f"Event is full: {booking.event_id}. Current bookings: {current_booking_count-1}, Capacity: {event_capacity}")
        raise HTTPException(status_code=400, detail="Event is full")

    booking_id = str(uuid.uuid4())
    new_booking_data = {
        "id": booking_id,
        "event_id": booking.event_id,
        "user_id": current_user["id"],
        "status": schemas.BookingStatus.CONFIRMED,
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow()
    }

    try:
        cassandra_session.execute(
            """
            INSERT INTO bookings (id, event_id, user_id, status, created_at, updated_at)
            VALUES (%s, %s, %s, %s, %s, %s)
            """,
            (
                new_booking_data["id"],
                new_booking_data["event_id"],
                new_booking_data["user_id"],
                new_booking_data["status"].value,
                new_booking_data["created_at"],
                new_booking_data["updated_at"]
            )
        )
        logger.info(f"Booking {booking_id} created successfully for event_id={booking.event_id}")
    except Exception as e:
        redis_client.decr(key)  # Rollback Redis increment if Cassandra insert fails
        logger.error(f"Failed to insert booking into Cassandra for event_id={booking.event_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to create booking")

    update_success = await update_event_capacity_in_catalog(booking.event_id, increment=True)
    if not update_success:
        redis_client.decr(key)
        cassandra_session.execute(
            "DELETE FROM bookings WHERE id = %s",
            (booking_id,)
        )
        logger.error(f"Failed to update event capacity in event-catalog-service for event_id={booking.event_id}. Booking rolled back.")
        raise HTTPException(status_code=500, detail="Failed to update event capacity. Booking rolled back.")

    background_tasks.add_task(
        send_booking_notification,
        new_booking_data["user_id"],
        new_booking_data["event_id"],
        "booking_confirmed"
    )

    return new_booking_data

@app.get("/bookings/user/{user_id}", response_model=List[schemas.BookingResponse])
async def get_user_bookings(
    user_id: str,
    current_user: dict = Depends(get_current_user),
    cassandra_session = Depends(get_cassandra)
):
    if user_id != current_user["id"]:
        raise HTTPException(status_code=403, detail="Not authorized to view these bookings")

    rows = cassandra_session.execute(
        "SELECT id, event_id, user_id, status, created_at, updated_at FROM bookings WHERE user_id = %s",
        (user_id,)
    )

    result = []
    for row in rows:
        event_details = None
        try:
            event_details = await get_event_details(str(row.event_id))
            if event_details is None:
                logger.warning(f"Could not retrieve details for event_id: {row.event_id} while fetching bookings for user_id: {user_id}")
        except Exception as e:
            logger.error(f"Error fetching event details for event_id {row.event_id}: {e}")

        booking_response = schemas.BookingResponse(
            id=str(row.id),
            event_id=str(row.event_id),
            user_id=str(row.user_id),
            status=row.status,
            created_at=row.created_at,
            updated_at=row.updated_at,
            event_details=event_details
        )
        result.append(booking_response)

    return result

@app.get("/bookings/event/{event_id}", response_model=List[schemas.BookingResponse])
async def get_event_bookings(
    event_id: str,
    current_user: dict = Depends(get_current_user),
    cassandra_session = Depends(get_cassandra)
):
    event = await get_event_details(str(event_id))
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    if event.get("organizer_id") != current_user["id"]:
        raise HTTPException(status_code=403, detail="Not authorized to view these bookings")

    rows = cassandra_session.execute(
        "SELECT id, event_id, user_id, status, created_at, updated_at FROM bookings WHERE event_id = %s",
        (event_id,)
    )

    result = []
    for row in rows:
        booking_response = schemas.BookingResponse(
            id=str(row.id),
            event_id=str(row.event_id),
            user_id=str(row.user_id),
            status=row.status,
            created_at=row.created_at,
            updated_at=row.updated_at,
            event_details=event
        )
        result.append(booking_response)

    return result

@app.delete("/bookings/{booking_id}")
async def cancel_booking(
    booking_id: str,
    background_tasks: BackgroundTasks,
    current_user: dict          = Depends(get_current_user),
    redis_client: redis.Redis   = Depends(get_redis),
    cassandra_session           = Depends(get_cassandra),
):
    row = cassandra_session.execute(
        "SELECT event_id, user_id FROM bookings WHERE id = %s",
        (booking_id,)
    ).one()
    if not row:
        raise HTTPException(status_code=404, detail="Booking not found")

    if row.user_id != current_user["id"]:
        raise HTTPException(status_code=403, detail="Not authorized to delete this booking")

    cassandra_session.execute(
        "DELETE FROM bookings WHERE id = %s",
        (booking_id,)
    )

    key = f"booking_count:{row.event_id}"
    redis_client.decr(key)

    update_success = await update_event_capacity_in_catalog(row.event_id, increment=False)
    if not update_success:
        redis_client.incr(key)
        cassandra_session.execute(
            "INSERT INTO bookings (id, event_id, user_id, status, created_at, updated_at) VALUES (%s, %s, %s, %s, toTimestamp(now()), toTimestamp(now()))",
            (booking_id, row.event_id, row.user_id, 'confirmed')
        )
        logger.error(f"Failed to update event capacity in event-catalog-service for event_id={row.event_id}. Booking cancellation rolled back.")
        raise HTTPException(status_code=500, detail="Failed to update event capacity. Booking cancellation rolled back.")

    background_tasks.add_task(
        send_booking_notification,
        row.user_id,
        row.event_id,
        "booking_cancelled"
    )

    return {"message": "Booking deleted successfully"}
