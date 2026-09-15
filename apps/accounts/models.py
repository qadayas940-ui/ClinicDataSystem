"""
نماذج الحسابات والصلاحيات.

- Role: الأدوار (مالك/طبيب/منظم/مدقق بيانات).
- Permission / RolePermission: صلاحيات مرتبطة بالأدوار.
- User: مستخدم مخصص يرث AbstractUser مع دعم القفل وإجبار تغيير كلمة المرور.
- StaffProfile: ملف تعريفي إضافي للموظف.
"""
from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils import timezone


class Role(models.Model):
    """دور وظيفي داخل النظام."""

    CODE_OWNER = "owner"
    CODE_DOCTOR = "doctor"
    CODE_ORGANIZER = "organizer"
    CODE_AUDITOR = "data_auditor"

    CODE_CHOICES = [
        (CODE_OWNER, "المالك"),
        (CODE_DOCTOR, "طبيب"),
        (CODE_ORGANIZER, "منظّم"),
        (CODE_AUDITOR, "مدقق بيانات"),
    ]

    name = models.CharField("اسم الدور", max_length=80)
    code = models.CharField("الرمز", max_length=40, unique=True, choices=CODE_CHOICES)
    description = models.TextField("الوصف", blank=True, default="")
    is_system_role = models.BooleanField("دور نظام", default=False)
    permissions = models.JSONField("الصلاحيات", default=dict, blank=True)

    class Meta:
        verbose_name = "دور"
        verbose_name_plural = "الأدوار"
        ordering = ["name"]

    def __str__(self):
        return self.name


class Permission(models.Model):
    """صلاحية دقيقة داخل النظام."""

    code = models.CharField("الرمز", max_length=100, unique=True)
    name = models.CharField("الاسم", max_length=120)
    description = models.TextField("الوصف", blank=True, default="")
    category = models.CharField("التصنيف", max_length=80, blank=True, default="")

    class Meta:
        verbose_name = "صلاحية"
        verbose_name_plural = "الصلاحيات"
        ordering = ["category", "name"]

    def __str__(self):
        return self.name


class RolePermission(models.Model):
    """ربط الدور بالصلاحية."""

    role = models.ForeignKey(Role, verbose_name="الدور", on_delete=models.CASCADE, related_name="role_permissions")
    permission = models.ForeignKey(Permission, verbose_name="الصلاحية", on_delete=models.CASCADE, related_name="permission_roles")

    class Meta:
        verbose_name = "صلاحية دور"
        verbose_name_plural = "صلاحيات الأدوار"
        unique_together = ("role", "permission")

    def __str__(self):
        return f"{self.role} - {self.permission}"


class User(AbstractUser):
    """
    مستخدم مخصص للنظام.

    يضيف الدور والقسم ودعم القفل بعد محاولات فاشلة وإجبار تغيير كلمة
    المرور المؤقتة. كلمات المرور تُخزَّن دائماً مُجزّأة (Argon2).
    """

    role = models.ForeignKey(
        Role,
        verbose_name="الدور",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="users",
    )
    department = models.ForeignKey(
        "core.Department",
        verbose_name="القسم",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="users",
    )
    is_force_password_change = models.BooleanField("إجبار تغيير كلمة المرور", default=False)
    failed_login_attempts = models.PositiveIntegerField("محاولات الدخول الفاشلة", default=0)
    locked_until = models.DateTimeField("مقفل حتى", null=True, blank=True)
    last_login_ip = models.GenericIPAddressField("آخر عنوان IP", null=True, blank=True)
    created_by = models.ForeignKey(
        "self",
        verbose_name="أنشأه",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_users",
    )
    deactivated_at = models.DateTimeField("تاريخ التعطيل", null=True, blank=True)
    deactivated_by = models.ForeignKey(
        "self",
        verbose_name="عطّله",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="deactivated_users",
    )

    class Meta:
        verbose_name = "مستخدم"
        verbose_name_plural = "المستخدمون"

    def __str__(self):
        return self.get_full_name() or self.username

    @property
    def is_owner(self):
        """هل المستخدم مالكاً للنظام؟"""
        return bool(self.role and self.role.code == Role.CODE_OWNER)

    @property
    def is_doctor(self):
        return bool(self.role and self.role.code == Role.CODE_DOCTOR)

    @property
    def is_organizer(self):
        return bool(self.role and self.role.code == Role.CODE_ORGANIZER)

    @property
    def is_auditor(self):
        return bool(self.role and self.role.code == Role.CODE_AUDITOR)

    @property
    def is_locked(self):
        """هل الحساب مقفل حالياً؟"""
        return bool(self.locked_until and self.locked_until > timezone.now())

    def lock_account(self, minutes):
        """قفل الحساب لمدة محددة بالدقائق."""
        self.locked_until = timezone.now() + timezone.timedelta(minutes=minutes)
        self.save(update_fields=["locked_until"])

    def reset_failed_attempts(self):
        """تصفير عدّاد المحاولات الفاشلة وإلغاء القفل."""
        self.failed_login_attempts = 0
        self.locked_until = None
        self.save(update_fields=["failed_login_attempts", "locked_until"])


class StaffProfile(models.Model):
    """ملف تعريفي إضافي للموظف."""

    user = models.OneToOneField(User, verbose_name="المستخدم", on_delete=models.CASCADE, related_name="profile")
    display_name = models.CharField("الاسم المعروض", max_length=120, blank=True, default="")
    phone = models.CharField("الهاتف", max_length=40, blank=True, default="")
    specialization = models.CharField("التخصص", max_length=120, blank=True, default="")
    notes = models.TextField("ملاحظات", blank=True, default="")

    class Meta:
        verbose_name = "ملف موظف"
        verbose_name_plural = "ملفات الموظفين"

    def __str__(self):
        return self.display_name or self.user.username
