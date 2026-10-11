import uuid
from dataclasses import dataclass
from typing import Dict, Any
from src.backend.adapters.out_bound.cache_gateway import ICacheGateway
from src.backend.adapters.out_bound.queue_gateway import IQueueGateway
from src.backend.core.domain.exceptions.registration_exceptions import (
    SectionFullException,
    ScheduleConflictException,
    PrerequisiteNotMetException,
    CreditLimitExceededException,
    AlreadyRegisteredException,
    DomainException
)

@dataclass(frozen=True)
class RegisterCourseCommand:
    student_id: str
    section_id: str
    semester_id: str
    prerequisite_course_code: str
    section_time_mask: int
    credits: int

class RegisterCourseUseCase:
    def __init__(self, cache_gateway: ICacheGateway, queue_gateway: IQueueGateway):
        self.cache_gateway = cache_gateway
        self.queue_gateway = queue_gateway

    async def execute(self, command: RegisterCourseCommand) -> Dict[str, Any]:
        # 1. Thẩm định toàn diện & Trừ slot nguyên tử qua Redis Lua script (O(1) in-memory)
        reserve_result = await self.cache_gateway.atomic_reserve_slot(
            student_id=command.student_id,
            section_id=command.section_id,
            prerequisite_course_code=command.prerequisite_course_code,
            section_time_mask=command.section_time_mask,
            credits=command.credits
        )
        
        code = reserve_result.get("code")
        if code == -1:
            raise AlreadyRegisteredException()
        elif code == -2:
            raise SectionFullException()
        elif code == -3:
            raise PrerequisiteNotMetException()
        elif code == -4:
            raise CreditLimitExceededException()
        elif code == -5:
            raise ScheduleConflictException()
        elif code != 1:
            raise DomainException(reserve_result.get("message", "Lỗi kiểm tra nghiệp vụ"))

        # 2. Sinh ticket_id ngẫu nhiên
        ticket_id = str(uuid.uuid4())

        # 3. Lưu trạng thái ban đầu PENDING vào Redis (để sinh viên Polling)
        await self.cache_gateway.set_ticket_status(ticket_id=ticket_id, status="PENDING")

        # 4. Đẩy payload tác vụ vào RabbitMQ buffer
        payload = {
            "ticket_id": ticket_id,
            "student_id": command.student_id,
            "section_id": command.section_id,
            "semester_id": command.semester_id,
            "credits": command.credits,
            "section_time_mask": command.section_time_mask
        }
        await self.queue_gateway.publish_registration_job(payload)

        return {
            "ticket_id": ticket_id,
            "status": "PENDING",
            "message": "Đã giữ chỗ thành công. Yêu cầu đang được xử lý trong hàng đợi."
        }
