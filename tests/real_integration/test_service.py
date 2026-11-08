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

    async def test_late_second_cancel_is_terminal_without_touching_new_registration(self):
        ctx=await self.service.contexts.load_registration_context("s1","sec")
        first=await self.store.reserve(ctx,"t1","key1","hash")
        await self.service.process(first.ticket_id)
        reg=await self.repo.get_operation("t1")
        await self.store.create_drop(ctx,"d1",reg.registration_id,"t1","drop1")
        await self.store.create_drop(ctx,"d2",reg.registration_id,"t1","drop2")
        await self.service.process("d1")
        await self.store.reserve(ctx,"t2","key2","hash")
        await self.service.process("t2")
        await self.service.process("d2")
        self.assertEqual((await self.service.status("d2","s1")).status,"FAILED")
        self.assertEqual((await self.repo.get_operation("t2")).status,"CONFIRMED")
        self.assertEqual(await self.redis.hget(self.prefix+"section:sec:owners","s1"),"t2")
        self.assertEqual(await self.store.pending(),[])

    async def test_process_reports_committed_outcome(self):
        ctx=await self.service.contexts.load_registration_context("s1","sec")
        await self.store.reserve(ctx,"t1","key1","hash")
        op=await self.service.process("t1")
        self.assertEqual(op.status,"CONFIRMED")

    async def test_real_broker_acceptance_redelivery_and_postcommit_cache_failure(self):
        from src.backend.infrastructure.messaging.rabbitmq_client import RabbitMQManager
        from unittest.mock import patch
        broker=RabbitMQManager("amqp://guest:guest@localhost:15673/")
        channel=await broker.get_channel()
        queue=await channel.get_queue("registration_queue")
        await queue.purge()
        class AcceptedThenTimeout:
            async def publish(self, name, payload):
                await broker.publish(name,payload)
                raise TimeoutError("confirmation lost after real broker acceptance")
        self.service.queue=AcceptedThenTimeout()
        try:
            with self.assertRaises(TimeoutError):
                await self.service.register("s1","sec","real-broker")
            message=await queue.get(timeout=5)
            import json
            ticket=json.loads(message.body)["ticket_id"]
            with patch.object(self.store,"finish",side_effect=ConnectionError("Redis unavailable after commit")):
                with self.assertRaises(ConnectionError):
                    await self.service.process(ticket)
            self.assertEqual((await self.repo.get_operation(ticket)).status,"CONFIRMED")
            await message.nack(requeue=True)
            again=await queue.get(timeout=5)
            self.assertTrue(again.redelivered)
            await self.service.process(ticket)
            await again.ack()
            self.assertEqual((await self.store.get_operation(ticket)).status,"CONFIRMED")
            self.assertEqual(await self.redis.get(self.prefix+"section:sec:slots"),"0")
        finally:
            await broker.close()

    async def test_terminal_metadata_expires_but_pending_does_not(self):
        ctx=await self.service.contexts.load_registration_context("s1","sec")
        await self.store.reserve(ctx,"retained","key","hash")
        self.assertEqual(await self.redis.ttl(self.prefix+"op:retained"),-1)
        await self.service.process("retained")
        self.assertGreater(await self.redis.ttl(self.prefix+"op:retained"),0)
        self.assertGreater(await self.redis.ttl(self.prefix+"idem:key"),0)
