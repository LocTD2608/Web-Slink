import os
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from src.backend.infrastructure.database.models import Base, StudentModel, CourseModel, SemesterModel, CourseSectionModel

URL = os.getenv("TEST_DATABASE_URL", "postgresql+asyncpg://postgres:postgres@localhost:15432/course_test")

async def fixture():
    if not URL.rsplit("/", 1)[-1].endswith("_test"):
        raise RuntimeError("Integration fixture requires a dedicated *_test database")
    engine = create_async_engine(URL)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with factory() as s:
        s.add_all([SemesterModel(id="sem", semester_code="test", name="Test", is_active=True),
                   StudentModel(id="s1", student_code="S1", full_name="One", email="one@test", major="CS", academic_year=2026, max_credits=24),
                   StudentModel(id="s2", student_code="S2", full_name="Two", email="two@test", major="CS", academic_year=2026, max_credits=24),
                   CourseModel(id="c0", course_code="PRE", course_name="Prerequisite", credits=3, department="CS"),
                   CourseModel(id="c1", course_code="CS", course_name="Course", credits=3, department="CS")])
        await s.flush()
        s.add(CourseSectionModel(id="sec", section_code="CS-1", course_id="c1", semester_id="sem",
            instructor="Teacher", classroom="A", schedule_day=8, start_period=10, end_period=12,
            time_mask=0, max_capacity=1, current_enrolled=0))
        await s.commit()
    return engine, factory
