from fastapi import Request, HTTPException, status
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response, JSONResponse
from jose import jwt, JWTError
from src.backend.infrastructure.webserver.config import config

class InMemoryAuthMiddleware(BaseHTTPMiddleware):
    """
    Middleware xác thực JWT hoàn toàn trong bộ nhớ (In-Memory HMAC-SHA256).
    Triệt tiêu 100% nút thắt tính toán Bcrypt/Argon2 và truy vấn DB trong đợt test tải 3.000 VUs.
    """
    async def dispatch(self, request: Request, call_next):
        # Bỏ qua xác thực cho các public endpoint (Health check, Docs, Catalog)
        path = request.url.path
        if (
            path in ["/", "/health", "/docs", "/openapi.json"]
            or path.startswith("/api/v1/sections")
            or path.startswith("/api/v1/registrations/status")
        ):
            return await call_next(request)

        # 1. Kiểm tra header Authorization
        auth_header = request.headers.get("Authorization")
        student_id = None

        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header.split(" ")[1]
            try:
                # Giải mã chữ ký đối xứng trong RAM O(1) CPU
                payload = jwt.decode(token, config.jwt_secret, algorithms=[config.jwt_algorithm])
                student_id = payload.get("sub") or payload.get("student_id")
            except JWTError:
                return JSONResponse(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    content={"detail": "Chữ ký JWT không hợp lệ hoặc đã hết hạn"}
                )

        # 2. Hỗ trợ fallback header X-Student-Id cho demo và curl test nhanh
        if not student_id:
            student_id = request.headers.get("X-Student-Id")

        if not student_id and request.method in ["POST", "DELETE"]:
            return JSONResponse(
                status_code=status.HTTP_401_UNAUTHORIZED,
                content={"detail": "Yêu cầu cung cấp Authorization Bearer Token hoặc X-Student-Id"}
            )

        request.state.student_id = student_id
        return await call_next(request)
