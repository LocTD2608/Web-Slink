from dataclasses import dataclass
from typing import Dict, Any
from src.backend.adapters.out_bound.cache_gateway import ICacheGateway
from src.backend.adapters.out_bound.queue_gateway import IQueueGateway
from src.backend.adapters.out_bound.persistence_gateway import IPersistenceGateway

@dataclass(frozen=True)
class DropCourseCommand:
    registration_id: str
    student_id: str
    section_id: str
    credits: int
    section_time_mask: int

class DropCourseUseCase:
    def __init__(
        self,
        cache_gateway: ICacheGateway,
        queue_gateway: IQueueGateway,
        persistence_gateway: IPersistenceGateway
    ):
        self.cache_gateway = cache_gateway
        self.queue_gateway = queue_gateway
        self.persistence_gateway = persistence_gateway

    async def execute(self, command: DropCourseCommand) -> Dict[str, Any]:
        # 1. Trả lại slot và tín chỉ tức thì trên Redis Lua script
        await self.cache_gateway.atomic_release_slot(
            student_id=command.student_id,
            section_id=command.section_id,
            credits=command.credits,
            section_time_mask=command.section_time_mask
        )

        # 2. Đẩy tác vụ hủy vào Queue để Worker cập nhật DB bất đồng bộ
        payload = {
            "registration_id": command.registration_id,
            "student_id": command.student_id,
            "section_id": command.section_id
        }
        await self.queue_gateway.publish_drop_job(payload)

        return {
            "success": True,
            "message": "Đã hủy học phần thành công và hoàn trả sĩ số."
        }
