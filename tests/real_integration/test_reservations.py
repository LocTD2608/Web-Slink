import os, unittest, asyncio, uuid
from redis.asyncio import Redis, BlockingConnectionPool
from src.backend.core.domain.entities.registration_context import RegistrationContext

@unittest.skipUnless(os.getenv("RUN_REAL_INTEGRATION") == "1", "requires dedicated services")
class ReservationTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        from src.backend.infrastructure.cache.reservation_store import ReservationStore
        self.redis = Redis(connection_pool=BlockingConnectionPool.from_url(
            "redis://localhost:16379/15", decode_responses=True, max_connections=50, timeout=30))
        self.prefix = "test:" + str(uuid.uuid4()) + ":"
        self.store = ReservationStore(self.redis, self.prefix)
        await self.redis.set(self.prefix + "section:sec:slots", 60)

    async def asyncTearDown(self):
        keys = [k async for k in self.redis.scan_iter(self.prefix + "*")]
        if keys:
            await self.redis.delete(*keys)
        await self.redis.aclose()

    def ctx(self, student="s1", section="sec", slots=None):
        return RegistrationContext(student, section, "sem", 3, 24, None, slots or [81,82,83])

    async def test_sixty_unique_winners(self):
        async def register(i):
            try:
                return await self.store.reserve(self.ctx(str(i)), str(i), "key"+str(i), "hash")
            except ValueError as e:
                return str(e)
        results = await asyncio.gather(*(register(i) for i in range(500)))
        self.assertEqual(sum(not isinstance(x, str) for x in results), 60)
        self.assertEqual(results.count("SECTION_FULL"), 440)
        self.assertEqual(await self.redis.get(self.prefix+"section:sec:slots"), "0")

    async def test_retry_release_and_weekend(self):
        a = await self.store.reserve(self.ctx(), "t1", "key1", "hash")
        self.assertEqual((await self.store.reserve(self.ctx(), "t2", "key1", "hash")).ticket_id, a.ticket_id)
        with self.assertRaisesRegex(ValueError, "IDEMPOTENCY_CONFLICT"):
            await self.store.reserve(self.ctx(), "t3", "key1", "other")
        await self.redis.set(self.prefix+"section:other:slots", 2)
        with self.assertRaisesRegex(ValueError, "SCHEDULE_CONFLICT"):
            await self.store.reserve(self.ctx(section="other"), "t3", "key3", "hash")
        self.assertTrue(await self.store.release(self.ctx(), "t1"))
        self.assertFalse(await self.store.release(self.ctx(), "t1"))
        self.assertEqual(await self.redis.get(self.prefix+"section:sec:slots"), "60")
        await self.store.reserve(self.ctx(section="other"), "t4", "key4", "hash")
