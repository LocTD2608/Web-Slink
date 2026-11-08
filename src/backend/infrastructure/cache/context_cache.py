import json
from sqlalchemy import select
from src.backend.infrastructure.database.models import StudentModel, CompletedCourseModel, SemesterModel, CourseSectionModel, CourseModel
from src.backend.core.domain.entities.registration_context import RegistrationContext
from src.backend.core.domain.entities.operation import RegistrationError
from src.backend.core.domain.entities.time_slot import TimeSlot

async def warm_contexts(factory, redis):
    async with factory() as s:
        students = (await s.scalars(select(StudentModel))).all()
        completed = {}
        for sid, code in (await s.execute(select(CompletedCourseModel.student_id, CompletedCourseModel.course_code))).all():
            completed.setdefault(sid, []).append(code)
        sections = (await s.execute(select(CourseSectionModel, CourseModel).join(CourseModel, CourseModel.id==CourseSectionModel.course_id))).all()
        codes = dict((await s.execute(select(CourseModel.id, CourseModel.course_code))).all())
        active = dict((await s.execute(select(SemesterModel.id, SemesterModel.is_active))).all())
        async with redis.pipeline(transaction=True) as p:
            for student in students:
                p.set("lab:context:student:"+student.id,json.dumps({"max_credits":student.max_credits,"completed_courses":completed.get(student.id,[])}))
            for sec, course in sections:
                p.set("lab:context:section:"+sec.id,json.dumps({"semester_id":sec.semester_id,"credits":course.credits,
                    "prerequisite_course_code":codes.get(course.prerequisite_course_id),"active":active[sec.semester_id],
                    "time_slots":TimeSlot(sec.schedule_day,sec.start_period,sec.end_period).period_indices()}))
            await p.execute()

class CachedContextRepository:
    def __init__(self, redis, fallback):
        self.redis,self.fallback=redis,fallback

    async def load_registration_context(self, student_id, section_id):
        student, section = await self.redis.mget(["lab:context:student:"+student_id,"lab:context:section:"+section_id])
        if not student or not section:
            return await self.fallback.load_registration_context(student_id,section_id)
        data = json.loads(section)
        if not data.pop("active"):
            raise RegistrationError("SEMESTER_CLOSED")
        ctx = RegistrationContext(student_id=student_id,section_id=section_id,**data,**json.loads(student))
        if section_id == "bench-section":
            generation = await self.redis.get("lab:run:flash")
            if not generation:
                raise RegistrationError("BENCHMARK_CLOSED")
            ctx.run_id,ctx.generation="flash",int(generation)
        return ctx
