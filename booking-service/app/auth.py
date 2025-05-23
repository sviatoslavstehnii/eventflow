import os
import logging

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError
import httpx
from dotenv import load_dotenv
from .consul_client import ConsulClient

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

SECRET_KEY = os.getenv("JWT_SECRET", "your-secret-key")
ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
AUTH_SERVICE_URL = os.getenv("AUTH_SERVICE_URL", "http://auth-service:8000") # Corrected port

oauth2_scheme = OAuth2PasswordBearer(tokenUrl=AUTH_SERVICE_URL + "/auth/login")
consul_client = ConsulClient()

async def get_current_user(token: str = Depends(oauth2_scheme)):
    auth_service_name = "auth-service"
    auth_service = consul_client.get_service(auth_service_name)
    if not auth_service:
        logger.error(f"{auth_service_name} not found in Consul.")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"{auth_service_name} is not available"
        )
    
    validate_url = f"http://{auth_service['host']}:{auth_service['port']}/users/me" # Use /users/me
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(
                validate_url,
                headers={"Authorization": f"Bearer {token}"}
            )
            if response.status_code == 200:
                return response.json() # Return whole user object
            logger.warning(f"Auth service validation failed with status {response.status_code}: {response.text}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication credentials",
                headers={"WWW-Authenticate": "Bearer"},
            )
        except httpx.RequestError:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Could not connect to auth service"
            )
