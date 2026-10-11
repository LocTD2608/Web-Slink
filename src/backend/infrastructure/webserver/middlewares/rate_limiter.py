from fastapi import Request, status
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse
import time
from collections import defaultdict
from threading import Lock

class TokenBucketRateLimiter(BaseHTTPMiddleware):
    """
    Middleware Token Bucket giới hạn tần suất gọi API trên mỗi IP/Client.
    Bổ trợ cho tầng Nginx L7 rate limiter.
    """
    def __init__(self, app, rate_per_second: float = 20.0, burst_capacity: int = 30):
        super().__init__(app)
        self.rate = rate_per_second
        self.capacity = burst_capacity
        self.tokens = defaultdict(lambda: burst_capacity)
        self.last_update = defaultdict(time.time)
        self.lock = Lock()

    async def dispatch(self, request: Request, call_next):
        client_ip = request.client.host if request.client else "unknown"
        now = time.time()

        with self.lock:
            elapsed = now - self.last_update[client_ip]
            self.last_update[client_ip] = now
            self.tokens[client_ip] = min(self.capacity, self.tokens[client_ip] + elapsed * self.rate)

            if self.tokens[client_ip] < 1.0:
                return JSONResponse(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    content={"detail": "Tần suất gửi yêu cầu quá nhanh, vui lòng thử lại sau giây lát."}
                )
            self.tokens[client_ip] -= 1.0

        return await call_next(request)
