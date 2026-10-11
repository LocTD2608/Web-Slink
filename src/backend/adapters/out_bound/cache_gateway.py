from abc import ABC, abstractmethod
from typing import Optional, Dict, Any, List

class ICacheGateway(ABC):
    """Cổng giao tiếp trừu tượng tới Redis In-Memory."""
    
    @abstractmethod
    async def atomic_reserve_slot(
        self,
        student_id: str,
        section_id: str,
        prerequisite_course_code: str,
        section_time_mask: int,
        credits: int
    ) -> Dict[str, Any]:
        """Thực thi Redis Lua script kiểm tra toàn diện và trừ slot nguyên tử."""
        pass

    @abstractmethod
    async def atomic_release_slot(
        self,
        student_id: str,
        section_id: str,
        credits: int,
        section_time_mask: int
    ) -> bool:
        """Thực thi Redis Lua script hoàn trả slot và số tín chỉ."""
        pass

    @abstractmethod
    async def set_ticket_status(self, ticket_id: str, status: str, reason: str = "") -> None:
        """Lưu trạng thái vé xử lý vào Redis."""
        pass

    @abstractmethod
    async def get_ticket_status(self, ticket_id: str) -> Optional[Dict[str, str]]:
        """Đọc trạng thái vé xử lý từ Redis (phục vụ Controlled Short Polling)."""
        pass

    @abstractmethod
    async def get_active_catalog(self) -> Optional[List[Dict[str, Any]]]:
        """Đọc toàn bộ danh mục 200 lớp học phần từ cache key catalog:active_sections."""
        pass

    @abstractmethod
    async def set_active_catalog(self, sections: List[Dict[str, Any]]) -> None:
        """Nạp danh mục lớp học phần vào Redis key catalog:active_sections."""
        pass
