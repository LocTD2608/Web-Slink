from sqlalchemy import select
from src.backend.infrastructure.database.models import CourseSectionModel, CourseModel, RegistrationModel
from src.backend.core.domain.entities.time_slot import TimeSlot

class CatalogRepository:
    def __init__(self, factory):
        self.factory = factory

    async def sections(self, student_id=None):
        async with self.factory() as s:
            stmt = select(CourseSectionModel, CourseModel).join(CourseModel, CourseModel.id == CourseSectionModel.course_id)
            if student_id:
                stmt = stmt.add_columns(RegistrationModel).join(RegistrationModel, RegistrationModel.section_id == CourseSectionModel.id).where(
                    RegistrationModel.student_id == student_id, RegistrationModel.status == "CONFIRMED")
            rows = (await s.execute(stmt)).all()
            codes = dict((await s.execute(select(CourseModel.id, CourseModel.course_code))).all())
            result = []
            for row in rows:
                sec, course = row[:2]
                item = {name: getattr(sec, name) for name in (
                    "id", "section_code", "semester_id", "instructor", "classroom", "schedule_day",
                    "start_period", "end_period", "max_capacity", "current_enrolled")}
                item.update(course_code=course.course_code, course_name=course.course_name,
                    credits=course.credits, department=course.department,
                    prerequisite_course_code=codes.get(course.prerequisite_course_id),
                    time_slots=TimeSlot(sec.schedule_day, sec.start_period, sec.end_period).period_indices(),
                    available_slots=sec.max_capacity-sec.current_enrolled)
                if student_id:
                    item.update(registration_id=row[2].id, ticket_id=row[2].ticket_id)
                result.append(item)
            return result
