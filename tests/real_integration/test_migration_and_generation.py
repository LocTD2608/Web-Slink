import os, unittest
from tests.real_integration.support import fixture
from src.backend.infrastructure.database.models import Base, BenchmarkRunModel, RegistrationModel
from src.backend.infrastructure.database.repositories.operation_repository import OperationRepository
from src.backend.infrastructure.database.repositories.context_repository import ContextRepository

@unittest.skipUnless(os.getenv("RUN_REAL_INTEGRATION") == "1", "requires dedicated services")
class MigrationTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.engine,self.factory=await fixture()
    async def asyncTearDown(self):
        await self.engine.dispose()
    async def test_create_tables_preserves_registration_and_stale_generation_rejected(self):
        repo=OperationRepository(self.factory)
        ctx=await ContextRepository(self.factory).load_registration_context("s1","sec")
        op=await repo.confirm_registration(ctx,"t","key","hash")
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        async with self.factory() as s:
            self.assertEqual((await s.get(RegistrationModel,op.registration_id)).status,"CONFIRMED")
            s.add(BenchmarkRunModel(id="flash",generation=2,accepting=True))
            await s.commit()
        ctx.run_id,ctx.generation="flash",1
        with self.assertRaisesRegex(ValueError,"STALE_GENERATION"):
            await repo.confirm_registration(ctx,"late","late-key","hash")
