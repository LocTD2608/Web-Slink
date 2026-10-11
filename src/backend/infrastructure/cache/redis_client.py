import os
from typing import Optional
import redis.asyncio as aioredis

class RedisClientManager:
    _instance: Optional["RedisClientManager"] = None
    _redis: Optional[aioredis.Redis] = None

    def __init__(self, redis_url: Optional[str] = None):
        self.redis_url = redis_url or os.getenv("REDIS_URL", "redis://localhost:6379/0")

    @classmethod
    def get_instance(cls, redis_url: Optional[str] = None) -> "RedisClientManager":
        if cls._instance is None:
            cls._instance = cls(redis_url)
        return cls._instance

    def get_client(self) -> aioredis.Redis:
        if self._redis is None:
            self._redis = aioredis.from_url(
                self.redis_url,
                encoding="utf-8",
                decode_responses=True,
                max_connections=500
            )
        return self._redis

    async def close(self) -> None:
        if self._redis is not None:
            await self._redis.close()
            self._redis = None
