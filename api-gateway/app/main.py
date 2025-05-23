import os
from fastapi import FastAPI, Request, Response, status
from fastapi.responses import JSONResponse
import httpx
from dotenv import load_dotenv

load_dotenv()

AUTH_URL = os.getenv("AUTH_URL", "http://auth-service:8000")
EVENT_URL = os.getenv("EVENT_URL", "http://event-catalog-service:8001")
BOOK_URL = os.getenv("BOOK_URL", "http://booking-service:8002")
NOTIF_URL = os.getenv("NOTIF_URL", "http://notification-service:8003")

app = FastAPI(title="EventFlow API Gateway")

PROXY_MAP = {
    "/auth": AUTH_URL,
    "/users": AUTH_URL,
    "/events": EVENT_URL,
    "/bookings": BOOK_URL,
    "/notifications": NOTIF_URL,
}

@app.api_route("/{full_path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH"])
async def proxy(full_path: str, request: Request):
    path = "/" + full_path
    for prefix, target in PROXY_MAP.items():
        if path.startswith(prefix):
            url = target + path
            break
    else:
        return JSONResponse({"detail": "Not found"}, status_code=404)


    method = request.method
    headers = dict(request.headers)
    body = await request.body()
    async with httpx.AsyncClient() as client:
        try:
            resp = await client.request(
                method, url, headers=headers, content=body, params=dict(request.query_params), timeout=30.0
            )
        except httpx.RequestError as e:
            return JSONResponse({"detail": f"Upstream error: {str(e)}"}, status_code=502)
    return Response(content=resp.content, status_code=resp.status_code, headers=resp.headers)
