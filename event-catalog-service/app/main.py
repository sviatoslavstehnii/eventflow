import http
from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorDatabase
from . import crud, schemas, auth
from .database import get_database
from typing import List, Optional
import logging
from .consul_client import ConsulClient

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Event Catalog Service")

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

@app.get("/events/", response_model=List[schemas.Event])
async def read_events(
    skip: int = 0,
    limit: int = 100,
    organizer_id: Optional[str] = None,
    is_active: Optional[bool] = None,
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    events = await crud.get_events(db, skip=skip, limit=limit, organizer_id=organizer_id, is_active=is_active)
    return events

@app.get("/events/{event_id}", response_model=schemas.Event)
async def read_event(event_id: str, db: AsyncIOMotorDatabase = Depends(get_database)):
    event = await crud.get_event(db, event_id)
    if event is None:
        raise HTTPException(status_code=404, detail="Event not found")
    return event

@app.post("/events/", response_model=schemas.Event, status_code=status.HTTP_201_CREATED)
async def create_event(
    event: schemas.EventCreate,
    db: AsyncIOMotorDatabase = Depends(get_database),
    current_user: dict = Depends(auth.get_current_user)
):
    return await crud.create_event(db=db, event=event, organizer_id=current_user["id"])

@app.put("/events/{event_id}", response_model=schemas.Event)
async def update_event(
    event_id: str,
    event: schemas.EventUpdate,
    db: AsyncIOMotorDatabase = Depends(get_database),
    current_user: dict = Depends(auth.get_current_user)
):
    db_event = await crud.get_event(db, event_id)
    if db_event is None:
        raise HTTPException(status_code=404, detail="Event not found")
    if db_event["organizer_id"] != current_user["id"]:
        raise HTTPException(status_code=403, detail="Not authorized to update this event")
    return await crud.update_event(db=db, event_id=event_id, event=event)

@app.delete("/events/{event_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_event(
    event_id: str,
    db: AsyncIOMotorDatabase = Depends(get_database),
    current_user: dict = Depends(auth.get_current_user)
):
    db_event = await crud.get_event(db, event_id)
    if db_event is None:
        raise HTTPException(status_code=404, detail="Event not found")
    if db_event["organizer_id"] != current_user["id"]:
        raise HTTPException(status_code=403, detail="Not authorized to delete this event")
    success = await crud.delete_event(db=db, event_id=event_id)
    if not success:
        raise HTTPException(status_code=500, detail="Failed to delete event")
