from contextlib import asynccontextmanager
from typing import Optional, List, Dict, Any
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from src.backend.adapters.out_bound.persistence_gateway import IPersistenceGateway
from src.backend.core.domain.entities.student import Student
from src.backend.core.domain.entities.course_section import CourseSection
from src.backend.core.domain.entities.registration import Registration
from src.backend.infrastructure.database.db_connection import AsyncSessionLocal
from src.backend.infrastructure.database.models import (
    StudentModel,
    CourseSectionModel,
    CourseModel,
    RegistrationModel,
    SemesterModel
)

class PostgresRegistrationRepository(IPersistenceGateway):
    def __init__(
        self,
        session: Optional[AsyncSession] = None,
        session_factory: Optional[async_sessionmaker[AsyncSession]] = None
    ):
        self._session = session
        self._session_factory = session_factory or AsyncSessionLocal

    @asynccontextmanager
    async def _get_session(self):
        if self._session is not None:
            yield self._session
        else:
            async with self._session_factory() as sess:
                yield sess

    async def get_student_by_id(self, student_id: str) -> Optional[Student]:
        async with self._get_session() as session:
            stmt = select(StudentModel).where(StudentModel.id == student_id)
            res = await session.execute(stmt)
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
        async with self._get_session() as session:
            stmt = select(CourseSectionModel, CourseModel).join(
                CourseModel, CourseSectionModel.course_id == CourseModel.id
            )
            if semester_id:
                stmt = stmt.where(CourseSectionModel.semester_id == semester_id)

            res = await session.execute(stmt)
            rows = res.all()
            result = []
            for sec, course in rows:
                result.append({
                    "id": sec.id,
                    "section_code": sec.section_code,
                    "course_code": course.course_code,
                    "course_name": course.course_name,
                    "credits": course.credits,
                    "prerequisite_course_code": "NONE",
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
        async with self._get_session() as session:
            stmt = select(CourseSectionModel, CourseModel).join(
                CourseModel, CourseSectionModel.course_id == CourseModel.id
            ).where(CourseSectionModel.id == section_id)
            
            res = await session.execute(stmt)
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
        async with self._get_session() as session:
            try:
                # 0. Kiểm tra trùng lặp bản ghi trước khi insert (Idempotent check)
                check_stmt = select(RegistrationModel).where(
                    RegistrationModel.student_id == registration.student_id,
                    RegistrationModel.section_id == registration.section_id,
                    RegistrationModel.status == "CONFIRMED"
                )
                existing = (await session.execute(check_stmt)).scalar_one_or_none()
                if existing:
                    return True

                # 1. Thêm bản ghi đăng ký vào bảng registrations
                reg_model = RegistrationModel(
                    id=registration.id,
                    ticket_id=registration.ticket_id,
                    student_id=registration.student_id,
                    section_id=registration.section_id,
                    semester_id=registration.semester_id,
                    status=registration.status
                )
                session.add(reg_model)

                # 2. Tăng current_enrolled của lớp học phần
                stmt = (
                    update(CourseSectionModel)
                    .where(CourseSectionModel.id == registration.section_id)
                    .values(current_enrolled=CourseSectionModel.current_enrolled + 1)
                )
                await session.execute(stmt)
                await session.commit()
                return True
            except Exception as exc:
                await session.rollback()
                # Kiểm tra lại xem bản ghi đã được ghi nhận trước đó thành công chưa
                try:
                    check_stmt = select(RegistrationModel).where(
                        RegistrationModel.student_id == registration.student_id,
                        RegistrationModel.section_id == registration.section_id,
                        RegistrationModel.status == "CONFIRMED"
                    )
                    existing = (await session.execute(check_stmt)).scalar_one_or_none()
                    if existing:
                        return True
                except Exception:
                    pass
                raise exc

    async def cancel_registration(self, registration_id: str) -> bool:
        async with self._get_session() as session:
            try:
                stmt = select(RegistrationModel).where(RegistrationModel.id == registration_id)
                res = await session.execute(stmt)
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
                await session.execute(upd)
                await session.commit()
                return True
            except Exception:
                await session.rollback()
                raise

    async def get_student_registrations(self, student_id: str, semester_id: Optional[str] = None) -> List[Dict[str, Any]]:
        async with self._get_session() as session:
            stmt = (
                select(RegistrationModel, CourseSectionModel, CourseModel)
                .join(CourseSectionModel, RegistrationModel.section_id == CourseSectionModel.id)
                .join(CourseModel, CourseSectionModel.course_id == CourseModel.id)
                .where(
                    RegistrationModel.student_id == student_id,
                    RegistrationModel.status == "CONFIRMED"
                )
            )
            if semester_id:
                stmt = stmt.where(RegistrationModel.semester_id == semester_id)

            res = await session.execute(stmt)
            rows = res.all()
            result = []
            for reg, sec, course in rows:
                result.append({
                    "id": sec.id,
                    "registration_id": reg.id,
                    "ticket_id": reg.ticket_id,
                    "section_code": sec.section_code,
                    "course_code": course.course_code,
                    "course_name": course.course_name,
                    "credits": course.credits,
                    "prerequisite_course_code": "NONE",
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
