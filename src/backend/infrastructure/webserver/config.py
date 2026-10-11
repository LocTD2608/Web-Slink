import os
from pydantic import BaseModel

class AppConfig(BaseModel):
    app_name: str = "Hệ thống Đăng ký Học phần Trực tuyến"
    environment: str = os.getenv("ENV", "development")
    jwt_secret: str = os.getenv("JWT_SECRET", "super-secret-course-reg-key-2026")
    jwt_algorithm: str = "HS256"
    redis_url: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    rabbitmq_url: str = os.getenv("RABBITMQ_URL", "amqp://guest:guest@localhost:5672/")
    database_url: str = os.getenv("DATABASE_URL", "postgresql+asyncpg://postgres:postgres@localhost:5432/course_reg")
    rate_limit_per_minute: int = 120

config = AppConfig()
