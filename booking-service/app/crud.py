from cassandra.cqlengine.connection import get_session
from .models import BookingModelCassandra # Assuming you rename/create this
from .schemas import Booking as BookingSchema, BookingStatus
from datetime import datetime
import logging
import os
import httpx

logger = logging.getLogger(__name__)
NOTIFICATION_SERVICE_URL = "http://notification-service:8003"

async def create_booking(session, booking_data: BookingSchema):
    logger.debug(f"Attempting to create booking in Cassandra: {booking_data}")
    try:
        insert_statement = session.prepare(
            f"INSERT INTO {session.keyspace}.bookings (id, event_id, user_id, status, created_at, updated_at) "
            "VALUES (?, ?, ?, ?, ?, ?)"
        )
        session.execute(
            insert_statement,
            (
                booking_data.id,
                booking_data.event_id,
                booking_data.user_id,
                booking_data.status.value,
                booking_data.created_at,
                booking_data.updated_at,
            ),
        )
        logger.info(f"Successfully created booking {booking_data.id} in Cassandra.")
        # Send notification to notification service
        await send_notification_to_service(
            user_id=booking_data.user_id,
            event_id=booking_data.event_id,
            booking_id=booking_data.id,
            status=booking_data.status.value,
            action="created"
        )
        return booking_data # Or fetch from DB to confirm
    except Exception as e:
        logger.error(f"Error creating booking in Cassandra: {e}")
        raise

async def get_booking_by_id(session, booking_id: str) -> BookingSchema | None:
    logger.debug(f"Fetching booking by ID: {booking_id} from Cassandra.")
    try:
        select_statement = session.prepare(f"SELECT * FROM {session.keyspace}.bookings WHERE id = ?")
        row = session.execute(select_statement, (booking_id,)).one()
        if row:
            return BookingSchema(**row._asdict()) # Convert Row to dict then to Pydantic model
        return None
    except Exception as e:
        logger.error(f"Error fetching booking by ID {booking_id} from Cassandra: {e}")
        raise

async def get_bookings_by_user(session, user_id: str) -> list[BookingSchema]:
    logger.debug(f"Fetching bookings for user_id: {user_id} from Cassandra.")
    try:
        select_statement = session.prepare(f"SELECT * FROM {session.keyspace}.bookings WHERE user_id = ?")
        rows = session.execute(select_statement, (user_id,))
        return [BookingSchema(**row._asdict()) for row in rows]
    except Exception as e:
        logger.error(f"Error fetching bookings for user {user_id} from Cassandra: {e}")
        raise

async def get_bookings_by_event(session, event_id: str) -> list[BookingSchema]:
    logger.debug(f"Fetching bookings for event_id: {event_id} from Cassandra.")
    try:
        select_statement = session.prepare(f"SELECT * FROM {session.keyspace}.bookings WHERE event_id = ?")
        rows = session.execute(select_statement, (event_id,))
        return [BookingSchema(**row._asdict()) for row in rows]
    except Exception as e:
        logger.error(f"Error fetching bookings for event {event_id} from Cassandra: {e}")
        raise

async def get_booking_by_user_and_event(session, user_id: str, event_id: str) -> BookingSchema | None:
    logger.debug(f"Fetching booking for user_id: {user_id} and event_id: {event_id}")
    try:
        select_statement = session.prepare(
            f"SELECT * FROM {session.keyspace}.bookings WHERE user_id = ? AND event_id = ? ALLOW FILTERING"
        )
        row = session.execute(select_statement, (user_id, event_id)).one()
        if row:
            return BookingSchema(**row._asdict())
        return None
    except Exception as e:
        logger.error(f"Error fetching booking for user {user_id} and event {event_id}: {e}")
        raise

async def update_booking_status(session, booking_id: str, status: BookingStatus) -> BookingSchema | None:
    logger.debug(f"Updating booking {booking_id} to status {status.value}")
    try:
        # First, fetch the booking to ensure it exists and to get its current state
        current_booking = await get_booking_by_id(session, booking_id)
        if not current_booking:
            logger.warning(f"Booking {booking_id} not found for status update.")
            return None

        update_statement = session.prepare(
            f"UPDATE {session.keyspace}.bookings SET status = ?, updated_at = ? WHERE id = ?"
        )
        updated_at_time = datetime.utcnow()
        session.execute(update_statement, (status.value, updated_at_time, booking_id))
        # Return the updated booking data
        current_booking.status = status
        current_booking.updated_at = updated_at_time
        logger.info(f"Successfully updated booking {booking_id} to status {status.value}")
        # Send notification to notification service
        await send_notification_to_service(
            user_id=current_booking.user_id,
            event_id=current_booking.event_id,
            booking_id=current_booking.id,
            status=status.value,
            action="updated"
        )
        return current_booking
    except Exception as e:
        logger.error(f"Error updating booking status for {booking_id}: {e}")
        raise

# Helper function to send notification
async def send_notification_to_service(user_id, event_id, booking_id, status, action):
    payload = {
        "user_id": user_id,
        "type": f"booking_{action}",
        "content": f"Booking {booking_id} for event {event_id} has been {action} with status {status}."
    }
    try:
        async with httpx.AsyncClient() as client:
            await client.post(f"{NOTIFICATION_SERVICE_URL}/notifications/send", json=payload)
    except Exception as e:
        logger.error(f"Failed to send notification to notification service: {e}")
