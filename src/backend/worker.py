import asyncio
import logging
import sys

from src.backend.infrastructure.messaging.rabbitmq_client import RabbitMQManager
from src.backend.infrastructure.cache.redis_client import RedisClientManager
from src.backend.infrastructure.cache.redis_cache_gateway import RedisCacheGateway
from src.backend.infrastructure.database.db_connection import AsyncSessionLocal
from src.backend.infrastructure.database.repositories.registration_repository import PostgresRegistrationRepository
from src.backend.adapters.in_bound.consumers.registration_consumer import RegistrationConsumer

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("worker")

async def main():
    logger.info("Initializing Background Registration Worker...")
    
    # 1. Khởi tạo kết nối RabbitMQ và Redis
    rmq_manager = RabbitMQManager.get_instance()
    redis_client = RedisClientManager.get_instance().get_client()
    cache_gateway = RedisCacheGateway(redis_client)
    
    # 2. Khởi tạo Database Session Factory và Persistence Gateway độc lập
    persistence_gateway = PostgresRegistrationRepository(session_factory=AsyncSessionLocal)
    
    consumer = RegistrationConsumer(
        rabbitmq_manager=rmq_manager,
        cache_gateway=cache_gateway,
        persistence_gateway=persistence_gateway
    )
    
    logger.info("Worker ready. Listening on RabbitMQ 'registration_queue'...")
    await consumer.start_consuming()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Worker stopped by user.")
