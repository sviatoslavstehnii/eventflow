import logging
import asyncio
import os
import aiosmtplib
import httpx
from .consul_client import ConsulClient

logging.basicConfig(level=logging.INFO)
consul_client = ConsulClient()

async def send_email(to_email: str, subject: str, body: str):
    message = f"Subject: {subject}\n\n{body}"
    await aiosmtplib.send(
        message,
        hostname="smtp.gmail.com",
        port=587,
        username=os.getenv("SMTP_USER"),
        password=os.getenv("SMTP_PASS"),
        use_tls=False
    )

async def process_notification(notification):
    try:
        await send_email(notification["user_id"], "Notification", notification["content"])
        logging.info(f"Notification sent: {notification['type']} to {notification['user_id']}")
    except Exception as e:
        logging.error(f"Failed to send notification: {str(e)}")
