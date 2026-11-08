import unittest, time
from fastapi.testclient import TestClient
from jose import jwt

class ApiSecurityTests(unittest.TestCase):
    def setUp(self):
        from src.backend.infrastructure.webserver.application import create_app
        self.client = TestClient(create_app(lab_mode=False, secret="test-secret"), raise_server_exceptions=False)
        self.headers = {"Authorization": "Bearer "+jwt.encode({"sub":"s1", "exp":time.time()+600}, "test-secret", algorithm="HS256"), "X-Idempotency-Key":"one"}

    def test_unsigned_header_cannot_register(self):
        self.assertEqual(self.client.post("/api/v1/registrations", headers={"X-Student-Id":"s1"}, json={"section_id":"sec"}).status_code, 401)

    def test_untrusted_business_fields_rejected(self):
        for payload in [{"section_id":"sec", "student_id":"s2"}, {"section_id":"sec", "credits":0}, {"section_id":"sec", "prerequisite_course_code":"NONE"}]:
            self.assertEqual(self.client.post("/api/v1/registrations", headers=self.headers, json=payload).status_code, 422)

    def test_other_student_list_forbidden_and_demo_disabled(self):
        self.assertEqual(self.client.get("/api/v1/registrations/student/s2", headers=self.headers).status_code, 403)
        self.assertEqual(self.client.post("/api/v1/lab/token", json={"student_id":"s1"}).status_code, 404)

    def test_health_and_metrics(self):
        self.assertEqual(self.client.get("/health").status_code, 200)
        self.client.get("/not-a-route-with-ticket-123")
        res = self.client.get("/metrics")
        self.assertEqual(res.status_code, 200)
        self.assertIn("registration_http_requests_total", res.text)
        self.assertNotIn("not-a-route-with-ticket-123", res.text)
