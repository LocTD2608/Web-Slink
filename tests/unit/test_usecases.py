import unittest
from unittest.mock import AsyncMock
import asyncio

from src.backend.core.usecases.register_course import RegisterCourseUseCase, RegisterCourseCommand
from src.backend.core.usecases.drop_course import DropCourseUseCase, DropCourseCommand
from src.backend.core.usecases.view_curriculum import ViewCurriculumUseCase
from src.backend.core.domain.exceptions.registration_exceptions import (
    SectionFullException,
    ScheduleConflictException,
    PrerequisiteNotMetException,
    CreditLimitExceededException,
    AlreadyRegisteredException
)

class TestUseCases(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.cache_gateway = AsyncMock()
        self.queue_gateway = AsyncMock()
        self.persistence_gateway = AsyncMock()

        self.register_usecase = RegisterCourseUseCase(
            cache_gateway=self.cache_gateway,
            queue_gateway=self.queue_gateway
        )
        self.drop_usecase = DropCourseUseCase(
            cache_gateway=self.cache_gateway,
            queue_gateway=self.queue_gateway,
            persistence_gateway=self.persistence_gateway
        )
        self.curriculum_usecase = ViewCurriculumUseCase(
            cache_gateway=self.cache_gateway,
            persistence_gateway=self.persistence_gateway
        )

    async def test_register_course_success(self):
        # Redis Lua script returns 1 for success
        self.cache_gateway.atomic_reserve_slot.return_value = {"code": 1, "message": "RESERVED"}
        
        command = RegisterCourseCommand(
            student_id="std-001",
            section_id="sec-001",
            semester_id="sem-2024-1",
            prerequisite_course_code="NONE",
            section_time_mask=7,
            credits=3
        )
        
        result = await self.register_usecase.execute(command)
        
        self.assertEqual(result["status"], "PENDING")
        self.assertIn("ticket_id", result)
        self.queue_gateway.publish_registration_job.assert_called_once()
        self.cache_gateway.set_ticket_status.assert_called_once()

    async def test_register_course_section_full(self):
        # Redis Lua script returns -2 for section full
        self.cache_gateway.atomic_reserve_slot.return_value = {"code": -2, "message": "SECTION_FULL"}
        
        command = RegisterCourseCommand(
            student_id="std-001",
            section_id="sec-001",
            semester_id="sem-2024-1",
            prerequisite_course_code="NONE",
            section_time_mask=7,
            credits=3
        )
        
        with self.assertRaises(SectionFullException):
            await self.register_usecase.execute(command)
            
        self.queue_gateway.publish_registration_job.assert_not_called()

    async def test_register_course_schedule_conflict(self):
        self.cache_gateway.atomic_reserve_slot.return_value = {"code": -5, "message": "SCHEDULE_CONFLICT"}
        
        command = RegisterCourseCommand(
            student_id="std-001",
            section_id="sec-001",
            semester_id="sem-2024-1",
            prerequisite_course_code="NONE",
            section_time_mask=7,
            credits=3
        )
        
        with self.assertRaises(ScheduleConflictException):
            await self.register_usecase.execute(command)

    async def test_view_curriculum_cache_hit(self):
        # Cache hit returns active sections json directly
        mock_sections = [{"id": "sec-001", "section_code": "CS101-01"}]
        self.cache_gateway.get_active_catalog.return_value = mock_sections
        
        sections = await self.curriculum_usecase.execute()
        self.assertEqual(len(sections), 1)
        self.assertEqual(sections[0]["section_code"], "CS101-01")
        self.persistence_gateway.get_active_sections.assert_not_called()

    async def test_drop_course_success(self):
        self.cache_gateway.atomic_release_slot.return_value = True
        
        command = DropCourseCommand(
            registration_id="reg-001",
            student_id="std-001",
            section_id="sec-001",
            credits=3,
            section_time_mask=7
        )
        
        res = await self.drop_usecase.execute(command)
        self.assertTrue(res["success"])
        self.cache_gateway.atomic_release_slot.assert_called_once()
        self.queue_gateway.publish_drop_job.assert_called_once()

if __name__ == "__main__":
    unittest.main()
