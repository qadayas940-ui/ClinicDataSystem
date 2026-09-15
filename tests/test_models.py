"""اختبارات النماذج الأساسية: المستخدم، الدور، القسم، والحذف الناعم."""
from django.contrib.auth import get_user_model
from django.test import TestCase

from apps.accounts.models import Role
from apps.core.models import Department

User = get_user_model()


class RoleModelTests(TestCase):
    """اختبار نموذج الدور."""

    def test_create_role(self):
        role = Role.objects.create(name="المالك", code=Role.CODE_OWNER, is_system_role=True)
        self.assertEqual(role.code, "owner")
        self.assertTrue(role.is_system_role)
        self.assertEqual(str(role), "المالك")


class DepartmentModelTests(TestCase):
    """اختبار نموذج القسم والحذف الناعم."""

    def test_create_department(self):
        dept = Department.objects.create(name="العيون", code="EYE")
        self.assertEqual(str(dept), "العيون")
        self.assertTrue(dept.is_active)

    def test_soft_delete(self):
        dept = Department.objects.create(name="المختبر", code="LAB")
        dept.soft_delete()
        # لم يُحذف فعلياً — لكنه غير ظاهر في المدير الافتراضي
        self.assertTrue(dept.is_deleted)
        self.assertFalse(Department.objects.filter(pk=dept.pk).exists())
        self.assertTrue(Department.all_objects.filter(pk=dept.pk).exists())

    def test_restore(self):
        dept = Department.objects.create(name="الأشعة", code="RAD")
        dept.soft_delete()
        dept.restore()
        self.assertFalse(dept.is_deleted)
        self.assertTrue(Department.objects.filter(pk=dept.pk).exists())


class UserModelTests(TestCase):
    """اختبار نموذج المستخدم المخصص."""

    def setUp(self):
        self.owner_role = Role.objects.create(name="المالك", code=Role.CODE_OWNER)
        self.doctor_role = Role.objects.create(name="طبيب", code=Role.CODE_DOCTOR)

    def test_create_user_hashed_password(self):
        user = User.objects.create_user(username="test1", password="StrongPass123")
        # كلمة المرور يجب ألا تُخزَّن كنص واضح
        self.assertNotEqual(user.password, "StrongPass123")
        self.assertTrue(user.check_password("StrongPass123"))

    def test_is_owner_property(self):
        owner = User.objects.create_user(username="owner1", password="x", role=self.owner_role)
        doctor = User.objects.create_user(username="doc1", password="x", role=self.doctor_role)
        self.assertTrue(owner.is_owner)
        self.assertFalse(doctor.is_owner)
        self.assertTrue(doctor.is_doctor)

    def test_lock_account(self):
        user = User.objects.create_user(username="lockme", password="x")
        self.assertFalse(user.is_locked)
        user.lock_account(10)
        self.assertTrue(user.is_locked)
        user.reset_failed_attempts()
        self.assertFalse(user.is_locked)
        self.assertEqual(user.failed_login_attempts, 0)
