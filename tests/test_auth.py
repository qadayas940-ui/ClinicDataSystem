"""اختبارات المصادقة: تسجيل الدخول، القفل، إعداد المالك، تغيير كلمة المرور."""
from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.urls import reverse

from apps.accounts.models import Role

User = get_user_model()


@override_settings(MAX_LOGIN_ATTEMPTS=5, LOGIN_LOCKOUT_MINUTES=10)
class LoginTests(TestCase):
    """اختبار تسجيل الدخول والقفل بعد المحاولات الفاشلة."""

    def setUp(self):
        self.owner_role = Role.objects.create(name="المالك", code=Role.CODE_OWNER)
        self.user = User.objects.create_user(
            username="doctor", password="CorrectPass123", role=self.owner_role
        )
        self.login_url = reverse("accounts:login")

    def test_successful_login(self):
        response = self.client.post(
            self.login_url, {"username": "doctor", "password": "CorrectPass123"}
        )
        self.assertRedirects(response, reverse("core:dashboard"))

    def test_failed_login_increments_counter(self):
        self.client.post(self.login_url, {"username": "doctor", "password": "wrong"})
        self.user.refresh_from_db()
        self.assertEqual(self.user.failed_login_attempts, 1)

    def test_account_locks_after_five_attempts(self):
        for _ in range(5):
            self.client.post(self.login_url, {"username": "doctor", "password": "wrong"})
        self.user.refresh_from_db()
        self.assertTrue(self.user.is_locked)
        # حتى بكلمة المرور الصحيحة لا يمكن الدخول أثناء القفل
        response = self.client.post(
            self.login_url, {"username": "doctor", "password": "CorrectPass123"}
        )
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.wsgi_request.user.is_authenticated)

    def test_successful_login_resets_counter(self):
        self.client.post(self.login_url, {"username": "doctor", "password": "wrong"})
        self.client.post(self.login_url, {"username": "doctor", "password": "CorrectPass123"})
        self.user.refresh_from_db()
        self.assertEqual(self.user.failed_login_attempts, 0)


class OwnerSetupTests(TestCase):
    """اختبار إعداد حساب المالك الأول."""

    def test_setup_page_accessible_when_no_owner(self):
        response = self.client.get(reverse("accounts:setup_owner"))
        self.assertEqual(response.status_code, 200)

    def test_login_redirects_to_setup_when_no_owner(self):
        response = self.client.get(reverse("accounts:login"))
        self.assertRedirects(response, reverse("accounts:setup_owner"))

    def test_create_owner(self):
        response = self.client.post(
            reverse("accounts:setup_owner"),
            {
                "full_name": "مالك النظام",
                "username": "owner",
                "email": "owner@example.com",
                "password": "SecurePass123",
                "password_confirm": "SecurePass123",
            },
        )
        self.assertRedirects(response, reverse("accounts:login"))
        owner = User.objects.get(username="owner")
        self.assertTrue(owner.is_owner)
        self.assertTrue(owner.check_password("SecurePass123"))
        self.assertNotEqual(owner.password, "SecurePass123")


class ForcePasswordChangeTests(TestCase):
    """اختبار إجبار تغيير كلمة المرور المؤقتة."""

    def setUp(self):
        self.role = Role.objects.create(name="طبيب", code=Role.CODE_DOCTOR)
        self.user = User.objects.create_user(
            username="temp", password="TempPass123", role=self.role,
            is_force_password_change=True,
        )

    def test_forced_redirect_to_change_password(self):
        self.client.force_login(self.user)
        response = self.client.get(reverse("core:dashboard"))
        self.assertRedirects(response, reverse("accounts:change_password"))

    def test_change_password_clears_flag(self):
        self.client.force_login(self.user)
        response = self.client.post(
            reverse("accounts:change_password"),
            {
                "old_password": "TempPass123",
                "new_password1": "BrandNewPass456",
                "new_password2": "BrandNewPass456",
            },
        )
        self.assertRedirects(response, reverse("core:dashboard"))
        self.user.refresh_from_db()
        self.assertFalse(self.user.is_force_password_change)
