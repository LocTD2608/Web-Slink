import unittest
from unittest.mock import AsyncMock, patch
from fastapi.testclient import TestClient

from src.backend.main import app
from src.backend.adapters.in_bound.controllers.catalog_controller import set_curriculum_usecase
from src.backend.adapters.in_bound.controllers.registration_controller import set_registration_usecases
from src.backend.adapters.in_bound.controllers.status_controller import set_status_cache_gateway
from src.backend.core.usecases.register_course import RegisterCourseUseCase
from src.backend.core.usecases.drop_course import DropCourseUseCase
from src.backend.core.usecases.view_curriculum import ViewCurriculumUseCase

class TestRegistrationApiFlow(unittest.TestCase):
    def setUp(self):
        self.mock_cache = AsyncMock()
        self.mock_queue = AsyncMock()
        self.mock_persistence = AsyncMock()

        self.register_uc = RegisterCourseUseCase(self.mock_cache, self.mock_queue)
        self.drop_uc = DropCourseUseCase(self.mock_cache, self.mock_queue, self.mock_persistence)
        self.curriculum_uc = ViewCurriculumUseCase(self.mock_cache, self.mock_persistence)

        set_curriculum_usecase(self.curriculum_uc)
        set_registration_usecases(self.register_uc, self.drop_uc)
        set_status_cache_gateway(self.mock_cache)

        self.client = TestClient(app, raise_server_exceptions=False)

    def test_health_check(self):
        res = self.client.get("/health")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json()["status"], "healthy")

    def test_get_sections_catalog(self):
        self.mock_cache.get_active_catalog.return_value = [
            {"id": "sec-01", "section_code": "CS101-01", "course_name": "Nhap mon Lap trinh", "available_slots": 25}
        ]
        res = self.client.get("/api/v1/sections")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]["section_code"], "CS101-01")

    def test_register_course_accepted(self):
        self.mock_cache.atomic_reserve_slot.return_value = {"code": 1, "message": "RESERVED"}
        
        payload = {
            "section_id": "sec-01",
            "semester_id": "sem-2024-1",
            "prerequisite_course_code": "NONE",
            "section_time_mask": 7,
            "credits": 3,
            "student_id": "std-001"
        }
        res = self.client.post(
            "/api/v1/registrations",
            json=payload,
            headers={"X-Student-Id": "std-001", "X-Idempotency-Key": "test-key-1"}
        )
        self.assertEqual(res.status_code, 202)
        body = res.json()
        self.assertEqual(body["status"], "PENDING")
        self.assertIn("ticket_id", body)

    def test_get_status_polling(self):
        self.mock_cache.get_ticket_status.return_value = {"status": "CONFIRMED", "reason": ""}
        res = self.client.get("/api/v1/registrations/status/ticket-abc-123")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json()["status"], "CONFIRMED")

if __name__ == "__main__":
    unittest.main()
