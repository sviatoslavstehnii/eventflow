from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from typing import Optional
import logging

from .database import get_db, engine
from . import models, schemas, crud
from .auth import create_access_token, get_current_user
from .auth import oauth2_scheme, revoked_tokens
from .consul_client import ConsulClient

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create database tables
models.Base.metadata.create_all(bind=engine)

app = FastAPI(title="Authentication Service")

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
    allow_origins=["*"],  # In production, replace with specific origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health")
async def health_check():
    """Health check endpoint for Consul"""
    return {"status": "healthy"}

@app.post("/auth/register", response_model=schemas.User)
def register_user(user: schemas.UserCreate, db: Session = Depends(get_db)):
    db_user = crud.get_user_by_email(db, email=user.email)
    if db_user:
        raise HTTPException(
            status_code=400,
            detail="Email already registered"
        )
    return crud.create_user(db=db, user=user)

@app.post("/auth/login")
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = crud.authenticate_user(db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token = create_access_token(data={"sub": user.email})
    return {"access_token": access_token, "token_type": "bearer"}

@app.post("/auth/logout")
def logout(token: str = Depends(oauth2_scheme)):
    revoked_tokens.add(token)
    return {"msg": "Token has been revoked; you have been logged out"}

@app.get("/users/me", response_model=schemas.User)
def read_users_me(current_user: models.User = Depends(get_current_user)):
    return current_user

@app.get("/auth/validate")
def validate_token(current_user: models.User = Depends(get_current_user)):
    return {"valid": True, "user": current_user}