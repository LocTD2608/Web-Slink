import time
import uuid
from dataclasses import asdict
from sqlalchemy import select
from src.backend.infrastructure.database.models import (
    StudentModel, CourseSectionModel, CourseModel, SemesterModel, RegistrationModel,
    OperationModel, CompletedCourseModel, BenchmarkRunModel,
)
from src.backend.core.domain.entities.operation import Operation, RegistrationError
from src.backend.core.domain.entities.time_slot import TimeSlot


def operation(row):
    return Operation(row.ticket_id, row.student_id, row.section_id, row.kind,
        row.status, row.generation, row.reason or "", row.registration_id)


class OperationRepository:
    def __init__(self, session_factory):
        self.factory = session_factory

    async def get_operation(self, ticket_id):
        async with self.factory() as s:
            row = await s.get(OperationModel, ticket_id)
            return operation(row) if row else None

    async def get_by_key(self, key, payload_hash):
        async with self.factory() as s:
            row = await s.scalar(select(OperationModel).where(OperationModel.idempotency_key == key))
            if row and row.payload_hash != payload_hash:
                raise RegistrationError("IDEMPOTENCY_CONFLICT")
            return operation(row) if row else None

    async def _student_lock(self, s, student_id):
        student = await s.scalar(select(StudentModel).where(StudentModel.id == student_id).with_for_update())
        if not student:
            raise RegistrationError("NOT_FOUND", 404)
        return student

    async def _generation(self, s, ctx):
        if ctx.run_id:
            run = await s.scalar(select(BenchmarkRunModel).where(BenchmarkRunModel.id == ctx.run_id).with_for_update(read=True))
            if not run or run.generation != ctx.generation:
                raise RegistrationError("STALE_GENERATION")

    async def confirm_registration(self, ctx, ticket_id, key, payload_hash):
        async with self.factory() as s, s.begin():
            await self._generation(s, ctx)
            student = await self._student_lock(s, ctx.student_id)
            previous = await s.scalar(select(OperationModel).where(OperationModel.idempotency_key == key))
            if previous:
                if previous.payload_hash != payload_hash:
                    raise RegistrationError("IDEMPOTENCY_CONFLICT")
                return operation(previous)
            terminal = await s.get(OperationModel, ticket_id)
            if terminal:
                return operation(terminal)
            section = await s.scalar(select(CourseSectionModel).where(CourseSectionModel.id == ctx.section_id).with_for_update())
            if not section:
                raise RegistrationError("NOT_FOUND", 404)
            semester = await s.get(SemesterModel, section.semester_id)
            if not semester.is_active:
                raise RegistrationError("SEMESTER_CLOSED")
            course = await s.get(CourseModel, section.course_id)
            existing = await s.scalar(select(RegistrationModel).where(
                RegistrationModel.student_id == ctx.student_id, RegistrationModel.section_id == ctx.section_id))
            if existing and existing.status == "CONFIRMED":
                raise RegistrationError("ALREADY_REGISTERED")
            if section.current_enrolled >= section.max_capacity:
                raise RegistrationError("SECTION_FULL")
            if course.prerequisite_course_id:
                prereq = await s.get(CourseModel, course.prerequisite_course_id)
                if not await s.get(CompletedCourseModel, (ctx.student_id, prereq.course_code)):
                    raise RegistrationError("PREREQUISITE_NOT_MET", 400)
            enrolled = (await s.execute(select(CourseSectionModel, CourseModel).join(
                RegistrationModel, RegistrationModel.section_id == CourseSectionModel.id).join(
                CourseModel, CourseModel.id == CourseSectionModel.course_id).where(
                RegistrationModel.student_id == ctx.student_id, RegistrationModel.status == "CONFIRMED",
                RegistrationModel.semester_id == section.semester_id))).all()
            if sum(c.credits for _, c in enrolled) + course.credits > student.max_credits:
                raise RegistrationError("CREDIT_LIMIT_EXCEEDED", 400)
            periods = set(TimeSlot(section.schedule_day, section.start_period, section.end_period).period_indices())
            if any(periods.intersection(TimeSlot(sec.schedule_day, sec.start_period, sec.end_period).period_indices()) for sec, _ in enrolled):
                raise RegistrationError("SCHEDULE_CONFLICT")
            if existing:
                existing.ticket_id, existing.status = ticket_id, "CONFIRMED"
                reg = existing
            else:
                reg = RegistrationModel(id=str(uuid.uuid4()), ticket_id=ticket_id, student_id=ctx.student_id,
                    section_id=ctx.section_id, semester_id=ctx.semester_id, status="CONFIRMED")
                s.add(reg)
            section.current_enrolled += 1
            row = OperationModel(ticket_id=ticket_id, student_id=ctx.student_id, section_id=ctx.section_id,
                kind="REGISTER", status="CONFIRMED", idempotency_key=key, payload_hash=payload_hash,
                registration_id=reg.id, generation=ctx.generation, reason="", created_at=time.time(), payload=asdict(ctx))
            s.add(row)
            await s.flush()
            return operation(row)

    async def fail_registration(self, ctx, ticket_id, key, payload_hash, reason):
        async with self.factory() as s, s.begin():
            await self._student_lock(s, ctx.student_id)
            row = await s.get(OperationModel, ticket_id)
            if row:
                return operation(row)
            row = OperationModel(ticket_id=ticket_id, student_id=ctx.student_id, section_id=ctx.section_id,
                kind="REGISTER", status="FAILED", idempotency_key=key, payload_hash=payload_hash,
                reason=reason, generation=ctx.generation, created_at=time.time(), payload=asdict(ctx))
            s.add(row)
            await s.flush()
            return operation(row)

    async def registration_for_drop(self, registration_id, student_id):
        async with self.factory() as s:
            reg = await s.get(RegistrationModel, registration_id)
            if not reg:
                raise RegistrationError("NOT_FOUND", 404)
            if reg.student_id != student_id:
                raise RegistrationError("FORBIDDEN", 403)
            if reg.status != "CONFIRMED":
                raise RegistrationError("NOT_CONFIRMED")
            return {"section_id": reg.section_id, "ticket_id": reg.ticket_id}

    async def cancel_registration(self, registration_id, student_id, expected_ticket_id, cancel_ticket_id, key):
        async with self.factory() as s, s.begin():
            await self._student_lock(s, student_id)
            previous = await s.scalar(select(OperationModel).where(OperationModel.idempotency_key == key))
            if previous:
                if previous.payload_hash != registration_id:
                    raise RegistrationError("IDEMPOTENCY_CONFLICT")
                return operation(previous)
            previous = await s.get(OperationModel, cancel_ticket_id)
            if previous:
                return operation(previous)
            reg = await s.get(RegistrationModel, registration_id)
            if not reg:
                raise RegistrationError("NOT_FOUND", 404)
            if reg.student_id != student_id:
                raise RegistrationError("FORBIDDEN", 403)
            stale = reg.ticket_id != expected_ticket_id
            sec = await s.scalar(select(CourseSectionModel).where(CourseSectionModel.id == reg.section_id).with_for_update())
            if not stale and reg.status == "CONFIRMED":
                reg.status = "CANCELLED"
                sec.current_enrolled -= 1
            old = await s.get(OperationModel, expected_ticket_id)
            if old and not stale:
                old.status = "CANCELLED"
            row = OperationModel(ticket_id=cancel_ticket_id, student_id=student_id, section_id=reg.section_id,
                kind="DROP", status="FAILED" if stale else "CANCELLED", idempotency_key=key, payload_hash=registration_id,
                registration_id=registration_id, reason="STALE_OPERATION" if stale else "", generation=old.generation if old else 0,
                created_at=time.time(), payload={"expected_ticket_id": expected_ticket_id})
            s.add(row)
            await s.flush()
            return operation(row)
