from sqlalchemy import select
from src.backend.infrastructure.database.models import StudentModel, CourseSectionModel, CourseModel, SemesterModel, CompletedCourseModel
from src.backend.core.domain.entities.time_slot import TimeSlot
from src.backend.core.domain.entities.registration_context import RegistrationContext
from src.backend.core.domain.entities.operation import RegistrationError

class ContextRepository:
    def __init__(self, session_factory):
        self.factory = session_factory

    async def load_registration_context(self, student_id: str, section_id: str) -> RegistrationContext:
        async with self.factory() as s:
            student = await s.get(StudentModel, student_id)
            section = await s.get(CourseSectionModel, section_id)
            if not student or not section:
                raise RegistrationError("NOT_FOUND", 404)
            semester = await s.get(SemesterModel, section.semester_id)
            if not semester.is_active:
                raise RegistrationError("SEMESTER_CLOSED")
            course = await s.get(CourseModel, section.course_id)
            pre = await s.get(CourseModel, course.prerequisite_course_id) if course.prerequisite_course_id else None
            completed = list((await s.scalars(select(CompletedCourseModel.course_code).where(CompletedCourseModel.student_id == student_id))).all())
            return RegistrationContext(student_id, section_id, section.semester_id, course.credits,
                student.max_credits, pre.course_code if pre else None,
                TimeSlot(section.schedule_day, section.start_period, section.end_period).period_indices(),
                completed_courses=completed)
