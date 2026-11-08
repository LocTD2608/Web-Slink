import unittest, time
from types import SimpleNamespace
from unittest.mock import AsyncMock
from fastapi.testclient import TestClient
from jose import jwt
from src.backend.infrastructure.webserver.application import create_app
from src.backend.core.domain.entities.operation import Operation

class TestRegistrationApiFlow(unittest.TestCase):
    def setUp(self):
        app = create_app(lab_mode=False, secret="test-secret")
        op = Operation("ticket", "s1", "sec", "REGISTER", "PENDING")
        app.state.service = SimpleNamespace(mode="postgres", register=AsyncMock(return_value=op), status=AsyncMock(return_value=op))
        app.state.catalog = SimpleNamespace(sections=AsyncMock(return_value=[{"id":"sec"}]))
        self.client = TestClient(app)
        self.headers = {"Authorization":"Bearer "+jwt.encode({"sub":"s1","exp":time.time()+600},"test-secret",algorithm="HS256"),"X-Idempotency-Key":"one"}

    def test_health_check(self):
        self.assertEqual(self.client.get("/health").status_code, 200)

    def test_get_sections_catalog(self):
        self.assertEqual(self.client.get("/api/v1/sections").json(), [{"id":"sec"}])

    def test_register_course_accepted(self):
        res = self.client.post("/api/v1/registrations", headers=self.headers, json={"section_id":"sec"})
        self.assertEqual(res.status_code, 202)
        self.assertEqual(res.json()["status"], "PENDING")

    def test_get_status_polling(self):
        res = self.client.get("/api/v1/registrations/status/ticket", headers=self.headers)
        self.assertEqual(res.json()["status"], "PENDING")
