from typing import Optional, List, Dict, Any
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from src.backend.adapters.out_bound.persistence_gateway import IPersistenceGateway
from src.backend.core.domain.entities.student import Student
from src.backend.core.domain.entities.course_section import CourseSection
from src.backend.core.domain.entities.registration import Registration
from src.backend.infrastructure.database.models import (
    StudentModel,
    CourseSectionModel,
    CourseModel,
    RegistrationModel,
    SemesterModel
)

class PostgresRegistrationRepository(IPersistenceGateway):
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_student_by_id(self, student_id: str) -> Optional[Student]:
        stmt = select(StudentModel).where(StudentModel.id == student_id)
        res = await self.session.execute(stmt)
        model = res.scalar_one_or_none()
        if not model:
            return None
        return Student(
            id=model.id,
            student_code=model.student_code,
            full_name=model.full_name,
            max_credits=model.max_credits,
            current_credits=0
        )

    async def get_active_sections(self, semester_id: Optional[str] = None) -> List[Dict[str, Any]]:
        stmt = select(CourseSectionModel, CourseModel).join(
            CourseModel, CourseSectionModel.course_id == CourseModel.id
        )
        if semester_id:
            stmt = stmt.where(CourseSectionModel.semester_id == semester_id)

        res = await self.session.execute(stmt)
        rows = res.all()
        result = []
        for sec, course in rows:
            result.append({
                "id": sec.id,
                "section_code": sec.section_code,
                "course_code": course.course_code,
                "course_name": course.course_name,
                "credits": course.credits,
                "instructor": sec.instructor,
                "classroom": sec.classroom,
                "schedule_day": sec.schedule_day,
                "start_period": sec.start_period,
                "end_period": sec.end_period,
                "time_mask": sec.time_mask,
                "max_capacity": sec.max_capacity,
                "current_enrolled": sec.current_enrolled,
                "available_slots": max(0, sec.max_capacity - sec.current_enrolled),
                "department": course.department
            })
        return result

    async def get_section_by_id(self, section_id: str) -> Optional[CourseSection]:
        stmt = select(CourseSectionModel, CourseModel).join(
            CourseModel, CourseSectionModel.course_id == CourseModel.id
        ).where(CourseSectionModel.id == section_id)
        
        res = await self.session.execute(stmt)
        row = res.first()
        if not row:
            return None
        sec, course = row
        return CourseSection(
            id=sec.id,
            section_code=sec.section_code,
            course_code=course.course_code,
            course_name=course.course_name,
            credits=course.credits,
            max_capacity=sec.max_capacity,
            current_enrolled=sec.current_enrolled,
            schedule_day=sec.schedule_day,
            start_period=sec.start_period,
            end_period=sec.end_period
        )

    async def save_registration(self, registration: Registration) -> bool:
        # 1. Thêm bản ghi đăng ký vào bảng registrations
        reg_model = RegistrationModel(
            id=registration.id,
            ticket_id=registration.ticket_id,
            student_id=registration.student_id,
            section_id=registration.section_id,
            semester_id=registration.semester_id,
            status=registration.status
        )
        self.session.add(reg_model)

        # 2. Tăng current_enrolled của lớp học phần
        stmt = (
            update(CourseSectionModel)
            .where(CourseSectionModel.id == registration.section_id)
            .values(current_enrolled=CourseSectionModel.current_enrolled + 1)
        )
        await self.session.execute(stmt)
        await self.session.commit()
        return True

    async def cancel_registration(self, registration_id: str) -> bool:
        stmt = select(RegistrationModel).where(RegistrationModel.id == registration_id)
        res = await self.session.execute(stmt)
        reg = res.scalar_one_or_none()
        if not reg:
            return False

        reg.status = "CANCELLED"
        # Giảm current_enrolled
        upd = (
            update(CourseSectionModel)
            .where(CourseSectionModel.id == reg.section_id)
            .values(current_enrolled=CourseSectionModel.current_enrolled - 1)
        )
        await self.session.execute(upd)
        await self.session.commit()
        return True
