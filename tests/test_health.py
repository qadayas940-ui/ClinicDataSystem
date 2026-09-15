"""اختبارات واجهة فحص الصحة."""
import json

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
        for key in ("status", "version", "db_status", "db_size_mb",
                    "trial_days_remaining", "server_time", "users_count"):
            self.assertIn(key, data)
        self.assertEqual(data["status"], "ok")
        self.assertEqual(data["db_status"], "connected")

    def test_health_db_connected(self):
        url = reverse("core:health_api")
        data = json.loads(self.client.get(url).content)
        self.assertEqual(data["db_status"], "connected")
