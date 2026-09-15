"""اختبارات واجهة فحص الصحة."""
import json

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse


class HealthCheckTests(TestCase):
    """اختبار نقطة GET /api/health/."""

    def test_health_endpoint_returns_json(self):
        url = reverse("core:health_api")
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "application/json")

    def test_health_payload_structure(self):
        url = reverse("core:health_api")
        response = self.client.get(url)
        data = json.loads(response.content)
        for key in ("status", "version"):
            self.assertIn(key, data)
        self.assertEqual(data["status"], "ok")
        self.assertNotIn("users_count", data)

    def test_health_db_connected(self):
        user = get_user_model().objects.create_user(username="health", password="StrongPass123")
        self.client.force_login(user)
        url = reverse("core:health_api")
        data = json.loads(self.client.get(url).content)
        self.assertEqual(data["db_status"], "connected")
