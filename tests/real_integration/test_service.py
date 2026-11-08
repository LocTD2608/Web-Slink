import os, unittest, uuid
from redis.asyncio import Redis
from tests.real_integration.support import fixture
from src.backend.infrastructure.database.repositories.context_repository import ContextRepository
from src.backend.infrastructure.database.repositories.operation_repository import OperationRepository
from src.backend.infrastructure.cache.reservation_store import ReservationStore

class QueueFailure:
    async def publish(self, *args):
        raise TimeoutError("broker confirmation lost")

@unittest.skipUnless(os.getenv("RUN_REAL_INTEGRATION") == "1", "requires dedicated services")
class ServiceTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        from src.backend.core.usecases.registration_service import RegistrationService
        self.engine, self.factory = await fixture()
        self.redis = Redis.from_url("redis://localhost:16379/15", decode_responses=True)
        self.prefix = "test:" + str(uuid.uuid4()) + ":"
        self.store = ReservationStore(self.redis, self.prefix)
        await self.redis.set(self.prefix+"section:sec:slots", 1)
        self.repo = OperationRepository(self.factory)
        self.service = RegistrationService(ContextRepository(self.factory), self.repo, self.store, QueueFailure(), "redis_queue")

    async def asyncTearDown(self):
        keys = [k async for k in self.redis.scan_iter(self.prefix+"*")]
        if keys: await self.redis.delete(*keys)
        await self.redis.aclose()
        await self.engine.dispose()

    async def test_publish_unknown_and_recovery_after_commit(self):
        with self.assertRaises(TimeoutError):
            await self.service.register("s1", "sec", "intent1")
        pending = await self.store.pending()
        self.assertEqual(len(pending), 1)
        self.assertEqual(await self.redis.get(self.prefix+"section:sec:slots"), "0")
        await self.service.process(pending[0])
        await self.service.process(pending[0])
        op = await self.service.status(pending[0], "s1")
        self.assertEqual(op.status, "CONFIRMED")
        with self.assertRaisesRegex(ValueError, "FORBIDDEN"):
            await self.service.status(pending[0], "s2")
        with self.assertRaises(TimeoutError):
            await self.service.drop(op.registration_id, "s1", "cancel1")
        drop = (await self.store.pending())[0]
        await self.service.process(drop)
        await self.service.process(drop)
        self.assertEqual((await self.service.status(drop, "s1")).status, "CANCELLED")
        self.assertEqual(await self.redis.get(self.prefix+"section:sec:slots"), "1")
