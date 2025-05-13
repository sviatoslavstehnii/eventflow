import logging
import asyncio
import os
import aiosmtplib
import httpx
from .consul_client import ConsulClient

logging.basicConfig(level=logging.INFO)
consul_client = ConsulClient()

async def send_email(to_email: str, subject: str, body: str):
    message = f"From: {os.getenv('SMTP_USER')}\r\n"
    message += f"To: {to_email}\r\n"
    message += f"Subject: {subject}\r\n"
    message += "\r\n"
    message += body
    await aiosmtplib.send(
        message,
        hostname="smtp.gmail.com",
        port=587,
        username=os.getenv("SMTP_USER"),
        password=os.getenv("SMTP_PASS"),
        sender=os.getenv("SMTP_USER"),
        recipients=[to_email],
        use_tls=False
    )

async def process_notification(notification):
    try:
        await send_email(notification["user_email"], "Notification", notification["content"])
        logging.info(f"Notification sent: {notification['type']} to {notification['user_id']}")
    except Exception as e:
        logging.error(f"Failed to send notification: {str(e)}")
