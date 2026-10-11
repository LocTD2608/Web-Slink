import os
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.backend.infrastructure.webserver.config import config
from src.backend.infrastructure.webserver.middlewares.auth_middleware import InMemoryAuthMiddleware
from src.backend.infrastructure.webserver.middlewares.idempotency_middleware import IdempotencyMiddleware
from src.backend.infrastructure.webserver.middlewares.rate_limiter import TokenBucketRateLimiter

from src.backend.infrastructure.cache.redis_client import RedisClientManager
from src.backend.infrastructure.cache.redis_cache_gateway import RedisCacheGateway
from src.backend.infrastructure.messaging.rabbitmq_client import RabbitMQManager
from src.backend.infrastructure.messaging.rabbitmq_queue_gateway import RabbitMQQueueGateway
from src.backend.infrastructure.database.db_connection import AsyncSessionLocal, create_tables
from src.backend.infrastructure.database.repositories.registration_repository import PostgresRegistrationRepository

from src.backend.core.usecases.register_course import RegisterCourseUseCase
from src.backend.core.usecases.drop_course import DropCourseUseCase
from src.backend.core.usecases.view_curriculum import ViewCurriculumUseCase

from src.backend.adapters.in_bound.controllers.catalog_controller import (
    router as catalog_router,
    set_curriculum_usecase
)
from src.backend.adapters.in_bound.controllers.registration_controller import (
    router as registration_router,
    set_registration_usecases
)
from src.backend.adapters.in_bound.controllers.status_controller import (
    router as status_router,
    set_status_cache_gateway
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("main")

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Initializing Course Registration System backend...")
    
    # 1. Dependency Injection Wiring
    redis_client = RedisClientManager.get_instance(config.redis_url).get_client()
    cache_gateway = RedisCacheGateway(redis_client)
    
    rmq_manager = RabbitMQManager.get_instance(config.rabbitmq_url)
    queue_gateway = RabbitMQQueueGateway(rmq_manager)
    
    # 2. Khởi tạo DB Session và Persistence Gateway cho fallback
    session = AsyncSessionLocal()
    persistence_gateway = PostgresRegistrationRepository(session)

    # 3. Khởi tạo Use Cases
    register_uc = RegisterCourseUseCase(cache_gateway=cache_gateway, queue_gateway=queue_gateway)
    drop_uc = DropCourseUseCase(
        cache_gateway=cache_gateway,
        queue_gateway=queue_gateway,
        persistence_gateway=persistence_gateway
    )
    curriculum_uc = ViewCurriculumUseCase(
        cache_gateway=cache_gateway,
        persistence_gateway=persistence_gateway
    )

    # 4. Gắn các use cases vào Controllers
    set_curriculum_usecase(curriculum_uc)
    set_registration_usecases(register_uc, drop_uc)
    set_status_cache_gateway(cache_gateway)

    # 5. Khởi tạo bảng CSDL nếu chưa có
    try:
        await create_tables()
        logger.info("Database schema initialized.")
    except Exception as e:
        logger.warning(f"Database schema auto-creation skipped: {e}")

    logger.info("Application wiring complete. Server is ready to handle traffic.")
    yield
    
    # Shutdown resources
    logger.info("Shutting down connections...")
    await session.close()
    await rmq_manager.close()
    await RedisClientManager.get_instance().close()

app = FastAPI(
    title=config.app_name,
    description="Hệ thống đăng ký học phần trực tuyến quy mô 3.000 sinh viên đồng thời (Clean Architecture)",
    version="2.2.0",
    lifespan=lifespan
)

# Cấu hình CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Cấu hình Middlewares theo thứ tự
app.add_middleware(TokenBucketRateLimiter, rate_per_second=30.0, burst_capacity=50)
app.add_middleware(IdempotencyMiddleware)
app.add_middleware(InMemoryAuthMiddleware)

# Đăng ký các REST API Routers
app.include_router(catalog_router)
app.include_router(registration_router)
app.include_router(status_router)

@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "service": "course-registration-backend",
        "version": "2.2.0"
    }

@app.get("/")
async def root():
    return {
        "message": "Cổng API Hệ thống Đăng ký Học phần Đại học",
        "docs": "/docs",
        "health": "/health"
    }
