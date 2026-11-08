import asyncio, os, unittest
from unittest.mock import patch
from types import SimpleNamespace
from redis.asyncio import Redis
from tests.real_integration.support import fixture
from src.backend.infrastructure.messaging.rabbitmq_client import RabbitMQManager
from src.backend.infrastructure.cache.reservation_store import ReservationStore
from src.backend.infrastructure.database.models import BenchmarkRunModel, CourseSectionModel

@unittest.skipUnless(os.getenv("RUN_REAL_INTEGRATION") == "1","requires dedicated services")
class ResetTests(unittest.IsolatedAsyncioTestCase):
    async def test_live_unacked_job_prevents_reset(self):
        from scripts import benchmark
        engine,factory=await fixture()
        broker=RabbitMQManager("amqp://guest:guest@localhost:15673/")
        r=Redis.from_url("redis://localhost:16379/15",decode_responses=True)
        message=None
        try:
            channel=await broker.get_channel()
            queue=await channel.get_queue("registration_queue")
            await queue.purge()
            await broker.publish("registration_queue",{"ticket_id":"held-for-reset-test"})
            message=await queue.get(timeout=5)
            service=SimpleNamespace(store=ReservationStore(r),queue=broker)
            with patch.dict(os.environ,{"RABBITMQ_MANAGEMENT_URL":"http://127.0.0.1:15684"}):
                for _ in range(15):
                    if not await benchmark.queues_empty(): break
                    await asyncio.sleep(1)
                self.assertFalse(await benchmark.queues_empty())
                async def existing_schema(): pass
                with patch.object(benchmark,"engine",engine), patch.object(benchmark,"AsyncSessionLocal",factory), patch.object(benchmark,"create_tables",existing_schema), patch.object(benchmark,"build_service",return_value=(service,None)), patch.object(benchmark.config,"lab_mode",True):
                    with self.assertRaisesRegex(RuntimeError,"Pending/queued"):
                        await benchmark.prepare("redis_queue")
                async with factory() as s:
                    self.assertEqual((await s.get(BenchmarkRunModel,"flash")).generation,0)
                    self.assertIsNone(await s.get(CourseSectionModel,"bench-section"))
        finally:
            # prepare closes its own broker; closing requeues an unacked test message.
            await broker.close()
            channel=await broker.get_channel()
            await (await channel.get_queue("registration_queue")).purge()
            await broker.close()
            await r.aclose()
            await engine.dispose()
