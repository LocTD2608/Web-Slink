import unittest
from unittest.mock import AsyncMock
import json

from src.backend.infrastructure.cache.redis_cache_gateway import RedisCacheGateway

class TestRedisLuaGateway(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.mock_redis = AsyncMock()
        self.gateway = RedisCacheGateway(self.mock_redis)

    async def test_atomic_reserve_slot_success(self):
        self.mock_redis.script_load.return_value = "dummy-sha-reserve"
        self.mock_redis.evalsha.return_value = 1  # 1 = SUCCESS
        
        result = await self.gateway.atomic_reserve_slot(
            student_id="std-100",
            section_id="sec-200",
            prerequisite_course_code="NONE",
            section_time_mask=7,
            credits=3
        )
        self.assertEqual(result["code"], 1)
        self.assertEqual(result["message"], "RESERVED")
        self.mock_redis.evalsha.assert_called_once()

    async def test_atomic_reserve_slot_section_full(self):
        self.mock_redis.script_load.return_value = "dummy-sha-reserve"
        self.mock_redis.evalsha.return_value = -2  # -2 = SECTION_FULL
        
        result = await self.gateway.atomic_reserve_slot(
            student_id="std-100",
            section_id="sec-200",
            prerequisite_course_code="NONE",
            section_time_mask=7,
            credits=3
        )
        self.assertEqual(result["code"], -2)
        self.assertEqual(result["message"], "SECTION_FULL")

    async def test_atomic_release_slot(self):
        self.mock_redis.script_load.return_value = "dummy-sha-rollback"
        self.mock_redis.evalsha.return_value = 1
        
        ok = await self.gateway.atomic_release_slot(
            student_id="std-100",
            section_id="sec-200",
            credits=3,
            section_time_mask=7
        )
        self.assertTrue(ok)

    async def test_catalog_caching(self):
        catalog_data = [{"id": "sec-1", "name": "Lap trinh Mang"}]
        await self.gateway.set_active_catalog(catalog_data)
        self.mock_redis.set.assert_called_once()

        self.mock_redis.get.return_value = json.dumps(catalog_data)
        loaded = await self.gateway.get_active_catalog()
        self.assertEqual(len(loaded), 1)
        self.assertEqual(loaded[0]["name"], "Lap trinh Mang")

    async def test_ticket_status(self):
        await self.gateway.set_ticket_status("t-123", "CONFIRMED")
        self.mock_redis.hset.assert_called_once()

        self.mock_redis.hgetall.return_value = {"status": "CONFIRMED"}
        status = await self.gateway.get_ticket_status("t-123")
        self.assertEqual(status["status"], "CONFIRMED")

if __name__ == "__main__":
    unittest.main()
