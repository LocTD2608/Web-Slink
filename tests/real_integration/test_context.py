import os
import unittest
from sqlalchemy import update
from tests.real_integration.support import fixture
from src.backend.infrastructure.database.models import CourseModel, SemesterModel

@unittest.skipUnless(os.getenv("RUN_REAL_INTEGRATION") == "1", "requires dedicated services")
class ContextTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.engine, self.factory = await fixture()

    async def asyncTearDown(self):
        await self.engine.dispose()

    async def test_context_and_unknown_ids(self):
        from src.backend.infrastructure.database.repositories.context_repository import ContextRepository
        repo = ContextRepository(self.factory)
        ctx = await repo.load_registration_context("s1", "sec")
        self.assertEqual(ctx.time_slots, [81, 82, 83])
        self.assertEqual(ctx.credits, 3)
        for student, section in [("missing", "sec"), ("s1", "missing")]:
            with self.assertRaisesRegex(ValueError, "NOT_FOUND"):
                await repo.load_registration_context(student, section)

    async def test_prerequisite_and_closed_semester(self):
        from src.backend.infrastructure.database.repositories.context_repository import ContextRepository
        async with self.factory() as s:
            await s.execute(update(CourseModel).where(CourseModel.id == "c1").values(prerequisite_course_id="c0"))
            await s.commit()
        repo = ContextRepository(self.factory)
        self.assertEqual((await repo.load_registration_context("s1", "sec")).prerequisite_course_code, "PRE")
        async with self.factory() as s:
            await s.execute(update(SemesterModel).values(is_active=False))
            await s.commit()
        with self.assertRaisesRegex(ValueError, "SEMESTER_CLOSED"):
            await repo.load_registration_context("s1", "sec")
