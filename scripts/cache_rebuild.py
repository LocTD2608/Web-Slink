"""Rebuild from DB only with API/worker stopped; never reset occupied seats."""
import asyncio, json
from redis.asyncio import Redis
from sqlalchemy import select
from src.backend.infrastructure.webserver.config import config
from src.backend.infrastructure.database.db_connection import AsyncSessionLocal
from src.backend.infrastructure.database.models import RegistrationModel, CourseSectionModel, CourseModel
from src.backend.infrastructure.database.repositories.catalog_repository import CatalogRepository
from src.backend.core.domain.entities.time_slot import TimeSlot

async def warmup_cache(factory=AsyncSessionLocal, redis_url=None):
    r = Redis.from_url(redis_url or config.redis_url, decode_responses=True)
    try:
        if await r.zcard("lab:pending"):
            raise RuntimeError("Pending operations: recover and drain before rebuilding cache")
        sections = await CatalogRepository(factory).sections()
        from src.backend.infrastructure.cache.context_cache import warm_contexts
        await warm_contexts(factory, r)
        async with factory() as s:
            regs = (await s.execute(select(RegistrationModel, CourseSectionModel, CourseModel)
                .join(CourseSectionModel, RegistrationModel.section_id == CourseSectionModel.id)
                .join(CourseModel, CourseSectionModel.course_id == CourseModel.id)
                .where(RegistrationModel.status == "CONFIRMED"))).all()
        student_keys = [k async for k in r.scan_iter("lab:student:*")]
        async with r.pipeline(transaction=True) as p:
            if student_keys: p.delete(*student_keys)
            for sec in sections:
                p.set(f"lab:section:{sec['id']}:slots", sec["available_slots"])
                p.delete(f"lab:section:{sec['id']}:owners")
            for reg, sec, course in regs:
                p.hset(f"lab:section:{sec.id}:owners", reg.student_id, reg.ticket_id)
                key = f"lab:student:{sec.semester_id}:{reg.student_id}"
                p.incrby(key+":credits", course.credits)
                p.sadd(key+":periods", *TimeSlot(sec.schedule_day, sec.start_period, sec.end_period).period_indices())
            p.set("lab:catalog", json.dumps(sections))
            await p.execute()
    finally:
        await r.aclose()
