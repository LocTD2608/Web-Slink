from fastapi import Request, status
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse
import logging
from src.backend.infrastructure.cache.redis_client import RedisClientManager

logger = logging.getLogger(__name__)

class IdempotencyMiddleware(BaseHTTPMiddleware):
    """
    Middleware kiểm tra X-Idempotency-Key nguyên tử trên Redis.
    Chặn đứng spam click đúp và network retry trước khi chạm vào Queue hoặc Lua script.
    """
    async def dispatch(self, request: Request, call_next):
        if request.method not in ["POST", "DELETE"] or not request.url.path.startswith("/api/v1/registrations"):
            return await call_next(request)

        idempotency_key = request.headers.get("X-Idempotency-Key")
        if not idempotency_key:
            return await call_next(request)

        try:
            redis_client = RedisClientManager.get_instance().get_client()
            # Thực thi nguyên tử SET key "PROCESSING" EX 60 NX
            lock_acquired = await redis_client.set(
                f"idempotency:{idempotency_key}",
                "PROCESSING",
                ex=60,
                nx=True
            )

            if not lock_acquired:
                # Key đã tồn tại -> Gói tin trùng lặp hoặc đang xử lý
                return JSONResponse(
                    status_code=status.HTTP_409_CONFLICT,
                    content={
                        "detail": "Yêu cầu đăng ký đang được xử lý hoặc đã gửi, vui lòng không nhấn liên tục",
                        "idempotency_key": idempotency_key
                    }
                )
        except Exception as e:
            logger.warning(f"Idempotency check skipped due to Redis error: {e}")

        return await call_next(request)
