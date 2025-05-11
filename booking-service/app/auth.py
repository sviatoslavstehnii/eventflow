import os
import logging

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError
import httpx
from dotenv import load_dotenv

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
    logger.info("get_current_user: start")
    logger.debug(f"Received raw token: {token!r}")

    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        async with httpx.AsyncClient(follow_redirects=True) as client:
            validate_url = f"{AUTH_SERVICE_URL}/auth/validate"
            logger.info(f"Calling auth service at {validate_url}")
            response = await client.get(
                validate_url,
                headers={"Authorization": f"Bearer {token}"}
            )

            logger.info(f"Auth-service response code: {response.status_code}")
            logger.debug(f"Auth-service response body: {response.text!r}")

            if response.status_code != 200:
                logger.warning("Token validation failed (non-200)")
                raise credentials_exception

            user_data = response.json()
            logger.info("Token validated successfully")
            logger.debug(f"Parsed user_data: {user_data}")

            if "user" not in user_data:
                logger.error("Response JSON missing 'user' key")
                raise credentials_exception

            logger.info(f"Authenticated user id: {user_data['user'].get('id')}")
            return user_data["user"]

    except httpx.RequestError as e:
        logger.error("HTTPX RequestError during token validation", exc_info=e)
        raise credentials_exception
    except JWTError as e:
        logger.error("JWTError parsing token", exc_info=e)
        raise credentials_exception
    except Exception as e:
        logger.exception("Unexpected error in get_current_user", exc_info=e)
        raise credentials_exception
