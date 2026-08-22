import time
from fastapi import Request, HTTPException, Response
from starlette.middleware.base import BaseHTTPMiddleware

class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Redis / In-Memory Sliding-Window Rate Limiter & Caching Middleware.
    Limits API requests to 100 requests per minute per IP / API key.
    """

    def __init__(self, app, max_requests: int = 100, window_seconds: int = 60):
        super().__init__(app)
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.request_records = {}

    async def dispatch(self, request: Request, call_next):
        client_ip = request.client.host if request.client else "127.0.0.1"
        api_key = request.headers.get("X-DigiIndia-Key", client_ip)

        now = time.time()
        if api_key not in self.request_records:
            self.request_records[api_key] = []

        # Filter timestamps outside window
        self.request_records[api_key] = [t for t in self.request_records[api_key] if now - t < self.window_seconds]

        if len(self.request_records[api_key]) >= self.max_requests:
            raise HTTPException(status_code=429, detail="API rate limit exceeded. Please wait 60 seconds.")

        self.request_records[api_key].append(now)

        response = await call_next(request)
        response.headers["X-RateLimit-Limit"] = str(self.max_requests)
        response.headers["X-RateLimit-Remaining"] = str(self.max_requests - len(self.request_records[api_key]))
        return response
