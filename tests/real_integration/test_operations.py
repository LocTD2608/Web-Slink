import os
import unittest
import asyncio
from dataclasses import asdict
from sqlalchemy import select, func
from tests.real_integration.support import fixture
from src.backend.infrastructure.database.models import RegistrationModel, CourseSectionModel
from src.backend.infrastructure.database.repositories.context_repository import ContextRepository

@unittest.skipUnless(os.getenv("RUN_REAL_INTEGRATION") == "1", "requires dedicated services")
class OperationsTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.engine, self.factory = await fixture()
        from src.backend.infrastructure.database.repositories.operation_repository import OperationRepository
        self.repo = OperationRepository(self.factory)
        self.ctx = await ContextRepository(self.factory).load_registration_context("s1", "sec")

    async def asyncTearDown(self):
        await self.engine.dispose()

    async def test_duplicate_commit_and_capacity(self):
        first = await self.repo.confirm_registration(self.ctx, "t1", "key1", "hash")
        again = await self.repo.confirm_registration(self.ctx, "t1", "key1", "hash")
        self.assertEqual(first.ticket_id, again.ticket_id)
        other = await ContextRepository(self.factory).load_registration_context("s2", "sec")
        with self.assertRaisesRegex(ValueError, "SECTION_FULL"):
            await self.repo.confirm_registration(other, "t2", "key2", "hash")
        async with self.factory() as s:
            self.assertEqual(await s.scalar(select(func.count()).select_from(RegistrationModel)), 1)
            self.assertEqual((await s.get(CourseSectionModel, "sec")).current_enrolled, 1)

    async def test_cancel_replay_and_new_ticket(self):
        first = await self.repo.confirm_registration(self.ctx, "t1", "key1", "hash")
        await self.repo.cancel_registration(first.registration_id, "s1", "t1", "d1", "drop1")
        await self.repo.cancel_registration(first.registration_id, "s1", "t1", "d1", "drop1")
        new = await self.repo.confirm_registration(self.ctx, "t2", "key2", "hash")
        await self.repo.cancel_registration(first.registration_id, "s1", "t1", "d1", "drop1")
        self.assertEqual((await self.repo.get_operation(new.ticket_id)).status, "CONFIRMED")
        async with self.factory() as s:
            self.assertEqual((await s.get(CourseSectionModel, "sec")).current_enrolled, 1)

    async def test_payload_conflict_and_owner(self):
        first = await self.repo.confirm_registration(self.ctx, "t1", "key1", "hash")
        with self.assertRaisesRegex(ValueError, "IDEMPOTENCY_CONFLICT"):
            await self.repo.confirm_registration(self.ctx, "t2", "key1", "different")
        with self.assertRaisesRegex(ValueError, "FORBIDDEN"):
            await self.repo.cancel_registration(first.registration_id, "s2", "t1", "d2", "drop2")
