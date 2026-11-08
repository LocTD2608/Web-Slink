from redis.asyncio import Redis, BlockingConnectionPool
from src.backend.infrastructure.webserver.config import config
from src.backend.infrastructure.database.db_connection import AsyncSessionLocal
from src.backend.infrastructure.database.repositories.context_repository import ContextRepository
from src.backend.infrastructure.database.repositories.operation_repository import OperationRepository
from src.backend.infrastructure.database.repositories.catalog_repository import CatalogRepository
from src.backend.infrastructure.cache.reservation_store import ReservationStore
from src.backend.infrastructure.messaging.rabbitmq_client import RabbitMQManager
from src.backend.core.usecases.registration_service import RegistrationService

def build_service():
    redis = Redis(connection_pool=BlockingConnectionPool.from_url(
        config.redis_url, decode_responses=True, max_connections=50, timeout=10))
    queue = RabbitMQManager(config.rabbitmq_url)
    service = RegistrationService(ContextRepository(AsyncSessionLocal), OperationRepository(AsyncSessionLocal),
        ReservationStore(redis), queue, config.registration_mode)
    return service, CatalogRepository(AsyncSessionLocal)
