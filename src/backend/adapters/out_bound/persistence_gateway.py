from abc import ABC, abstractmethod
from typing import Optional, List, Dict, Any
from src.backend.core.domain.entities.student import Student
from src.backend.core.domain.entities.course_section import CourseSection
from src.backend.core.domain.entities.registration import Registration

class IPersistenceGateway(ABC):
    """Cổng giao tiếp trừu tượng tới PostgreSQL Database."""
    
    @abstractmethod
    async def get_student_by_id(self, student_id: str) -> Optional[Student]:
        pass

    @abstractmethod
    async def get_active_sections(self, semester_id: Optional[str] = None) -> List[Dict[str, Any]]:
        pass

    @abstractmethod
    async def get_section_by_id(self, section_id: str) -> Optional[CourseSection]:
        pass

    @abstractmethod
    async def save_registration(self, registration: Registration) -> bool:
        pass

    @abstractmethod
    async def cancel_registration(self, registration_id: str) -> bool:
        pass
