import os
import logging

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
import httpx
from dotenv import load_dotenv
from jose import JWTError

load_dotenv()

# ——— Logging setup ———
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger("auth-dep")

# JWT Configuration
SECRET_KEY = os.getenv("JWT_SECRET", "your-secret-key")
ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
AUTH_SERVICE_URL = os.getenv("AUTH_SERVICE_URL", "http://auth-service:8001")

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")


async def get_current_user(token: str = Depends(oauth2_scheme)):
    logger.debug(f"[get_current_user] received token: {token!r}")
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        async with httpx.AsyncClient(follow_redirects=True) as client:
            validate_url = f"{AUTH_SERVICE_URL}/auth/validate"
            logger.debug(f"[get_current_user] calling {validate_url}")
            response = await client.get(
                validate_url,
                headers={"Authorization": f"Bearer {token}"}
            )
            logger.debug(f"[get_current_user] auth-service status: {response.status_code}")
            logger.debug(f"[get_current_user] auth-service body: {response.text!r}")

            if response.status_code != 200:
                logger.warning("[get_current_user] token validation failed")
                raise credentials_exception

            user_data = response.json()
            logger.info(f"[get_current_user] user_data: {user_data}")
            if "user" not in user_data:
                logger.error("[get_current_user] 'user' key missing in response")
                raise credentials_exception

            return user_data["user"]

    except httpx.RequestError as re:
        logger.error(f"[get_current_user] HTTPX error: {re!r}")
        raise credentials_exception
    except JWTError as je:
        logger.error(f"[get_current_user] JWT error: {je!r}")
        raise credentials_exception
    except Exception as e:
        # catch anything unexpected
        logger.exception(f"[get_current_user] unexpected error: {e!r}")
        raise credentials_exception
