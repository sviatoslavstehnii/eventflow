import os
import logging

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
import httpx
from dotenv import load_dotenv
from jose import JWTError
from .consul_client import ConsulClient

load_dotenv()

# ——— Logging setup ———
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger("auth-dep")

# JWT Configuration
SECRET_KEY = os.getenv("JWT_SECRET", "your-secret-key")
ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")
consul_client = ConsulClient()

async def get_current_user(token: str = Depends(oauth2_scheme)):
    auth_service = consul_client.get_service("auth-service")
    if not auth_service:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Auth service is not available"
        )
    
    auth_url = f"http://{auth_service['host']}:{auth_service['port']}/auth/validate"
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(
                auth_url,
                headers={"Authorization": f"Bearer {token}"}
            )
            if response.status_code == 200:
                return response.json()["user"]
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
