"""
النماذج الأساسية المشتركة (النواة).

يحتوي هذا الملف على:
- النماذج المجرّدة (Abstract) للطابع الزمني والحذف الناعم (Soft Delete).
- نماذج النظام: الأقسام، سجل التدقيق، إصدارات التطبيق، تاريخ التحديثات،
  حالة الترخيص، تاريخ النسخ الاحتياطي، إعدادات الخادم.
"""
from django.conf import settings
from django.db import models
from django.utils import timezone


class SoftDeleteQuerySet(models.QuerySet):
    """مجموعة استعلام تدعم الحذف الناعم."""

    def alive(self):
        """السجلات غير المحذوفة فقط."""
        return self.filter(deleted_at__isnull=True)

    def dead(self):
        """السجلات المحذوفة (حذف ناعم) فقط."""
        return self.filter(deleted_at__isnull=False)


class SoftDeleteManager(models.Manager):
    """مدير يُرجع السجلات غير المحذوفة افتراضياً."""

    def get_queryset(self):
        return SoftDeleteQuerySet(self.model, using=self._db).alive()


class AllObjectsManager(models.Manager):
    """مدير يُرجع كل السجلات بما فيها المحذوفة."""

    def get_queryset(self):
        return SoftDeleteQuerySet(self.model, using=self._db)


class TimeStampedModel(models.Model):
    """نموذج مجرّد يضيف حقلي الإنشاء والتحديث."""

    created_at = models.DateTimeField("تاريخ الإنشاء", auto_now_add=True)
    updated_at = models.DateTimeField("تاريخ التحديث", auto_now=True)

    class Meta:
        abstract = True


class SoftDeleteModel(TimeStampedModel):
    """نموذج مجرّد يدعم الحذف الناعم عبر الحقل deleted_at."""

    deleted_at = models.DateTimeField("تاريخ الحذف", null=True, blank=True)

    objects = SoftDeleteManager()
    all_objects = AllObjectsManager()

    class Meta:
        abstract = True

    def soft_delete(self):
        """حذف ناعم: يضع طابعاً زمنياً بدلاً من الحذف الفعلي."""
        self.deleted_at = timezone.now()
        self.save(update_fields=["deleted_at"])

    def restore(self):
        """استعادة سجل محذوف حذفاً ناعماً."""
        self.deleted_at = None
        self.save(update_fields=["deleted_at"])

    @property
    def is_deleted(self):
        return self.deleted_at is not None


class Department(SoftDeleteModel):
    """قسم داخل المنشأة (مثال: العيون، المختبر، الاستقبال)."""

    TYPE_CHOICES = [
        ("clinic", "عيادة"), ("laboratory", "مختبر"),
        ("diagnostic", "خدمة تشخيصية"), ("administration", "إدارة"),
    ]

    name = models.CharField("اسم القسم", max_length=120)
    code = models.CharField("الرمز", max_length=40, unique=True)
    description = models.TextField("الوصف", blank=True, default="")
    department_type = models.CharField("نوع القسم", max_length=20, choices=TYPE_CHOICES, default="clinic")
    is_active = models.BooleanField("نشط", default=True)

    class Meta:
        verbose_name = "قسم"
        verbose_name_plural = "الأقسام"
        ordering = ["name"]

    def __str__(self):
        return self.name


class ReferenceValue(SoftDeleteModel):
    """قيمة مرجعية مستخرجة من الملفات القديمة لاستخدامها في القوائم والبحث."""

    CATEGORY_CHOICES = [
        ("department", "قسم"),
        ("doctor", "طبيب"),
        ("organizer", "منظّم"),
        ("lab_test", "فحص مختبري"),
        ("referral_destination", "جهة إحالة"),
        ("diagnosis", "تشخيص / حالة"),
        ("area", "منطقة سكن"),
    ]

    category = models.CharField("التصنيف", max_length=40, choices=CATEGORY_CHOICES, db_index=True)
    canonical_name = models.CharField("الاسم الموحّد", max_length=255)
    normalized_name = models.CharField("مفتاح المطابقة", max_length=255, db_index=True)
    aliases = models.JSONField("الصيغ الأصلية", default=list, blank=True)
    source_sheets = models.JSONField("أوراق المصدر", default=list, blank=True)
    occurrence_count = models.PositiveIntegerField("عدد مرات الظهور", default=0)
    needs_review = models.BooleanField("يحتاج مراجعة", default=False)
    is_active = models.BooleanField("نشط", default=True)
    departments = models.ManyToManyField(
        Department,
        verbose_name="الأقسام المرتبطة",
        blank=True,
        related_name="reference_values",
        help_text="تُستخدم خصوصاً لربط الطبيب بقسم أو أكثر كما ورد في ملفات المصدر.",
    )

    class Meta:
        verbose_name = "قيمة مرجعية"
        verbose_name_plural = "القيم المرجعية"
        ordering = ["category", "canonical_name"]
        constraints = [
            models.UniqueConstraint(
                fields=["category", "normalized_name"],
                name="uniq_reference_category_normalized",
            ),
        ]

    def __str__(self):
        return self.canonical_name


class Notification(TimeStampedModel):
    """إشعار نظام قابل للقراءة والربط بكائن من دون تخزين بيانات طبية حساسة."""

    EVENT_CHOICES = [
        ("patient_created", "تسجيل مريض"),
        ("patient_updated", "تعديل مريض"),
        ("import_completed", "اكتمال استيراد"),
        ("import_failed", "خطأ استيراد"),
        ("system", "حدث نظام"),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name="المستخدم",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="notifications",
    )
    event_type = models.CharField("نوع الحدث", max_length=40, choices=EVENT_CHOICES, default="system")
    title = models.CharField("العنوان", max_length=160)
    message = models.CharField("الرسالة", max_length=300, blank=True, default="")
    object_type = models.CharField("نوع السجل المرتبط", max_length=80, blank=True, default="")
    object_id = models.CharField("معرّف السجل المرتبط", max_length=100, blank=True, default="")
    target_url = models.CharField("الرابط", max_length=300, blank=True, default="")
    read_at = models.DateTimeField("قُرئ في", null=True, blank=True)

    class Meta:
        verbose_name = "إشعار"
        verbose_name_plural = "الإشعارات"
        ordering = ["-created_at"]

    @property
    def is_read(self):
        return self.read_at is not None

    def __str__(self):
        return self.title


class AuditLog(models.Model):
    """سجل تدقيق للعمليات المهمة — بدون بيانات حساسة."""

    ACTION_CHOICES = [
        ("create", "إنشاء"),
        ("update", "تعديل"),
        ("delete", "حذف"),
        ("login", "تسجيل دخول"),
        ("logout", "تسجيل خروج"),
        ("login_failed", "محاولة دخول فاشلة"),
        ("view", "عرض"),
        ("export", "تصدير"),
        ("import", "استيراد"),
        ("other", "أخرى"),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name="المستخدم",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="audit_logs",
    )
    action = models.CharField("الإجراء", max_length=20, choices=ACTION_CHOICES)
    model_name = models.CharField("النموذج", max_length=100, blank=True, default="")
    object_id = models.CharField("معرّف السجل", max_length=100, blank=True, default="")
    object_repr = models.CharField("وصف السجل", max_length=255, blank=True, default="")
    changes = models.JSONField("التغييرات", null=True, blank=True)
    ip_address = models.GenericIPAddressField("عنوان IP", null=True, blank=True)
    user_agent = models.CharField("وكيل المتصفح", max_length=255, blank=True, default="")
    timestamp = models.DateTimeField("التوقيت", auto_now_add=True, db_index=True)

    class Meta:
        verbose_name = "سجل تدقيق"
        verbose_name_plural = "سجلات التدقيق"
        ordering = ["-timestamp"]

    def __str__(self):
        return f"{self.get_action_display()} - {self.model_name} @ {self.timestamp}"


class AppVersion(models.Model):
    """إصدارات التطبيق."""

    CHANNEL_CHOICES = [
        ("stable", "مستقر"),
        ("beta", "تجريبي"),
        ("develop", "تطوير"),
    ]

    version_number = models.CharField("رقم الإصدار", max_length=40, unique=True)
    release_date = models.DateField("تاريخ الإصدار", null=True, blank=True)
    channel = models.CharField("القناة", max_length=20, choices=CHANNEL_CHOICES, default="stable")
    notes = models.TextField("ملاحظات الإصدار", blank=True, default="")
    is_current = models.BooleanField("الإصدار الحالي", default=False)
    db_schema_version = models.CharField("إصدار مخطط قاعدة البيانات", max_length=40, default="1")

    class Meta:
        verbose_name = "إصدار التطبيق"
        verbose_name_plural = "إصدارات التطبيق"
        ordering = ["-release_date"]

    def __str__(self):
        return f"{self.version_number} ({self.get_channel_display()})"


class UpdateHistory(models.Model):
    """تاريخ عمليات تحديث التطبيق."""

    UPDATE_TYPE_CHOICES = [
        ("optional", "اختياري"),
        ("recommended", "موصى به"),
        ("security", "أمني"),
    ]
    STATUS_CHOICES = [
        ("pending", "قيد الانتظار"),
        ("in_progress", "قيد التنفيذ"),
        ("completed", "مكتمل"),
        ("failed", "فشل"),
        ("rolled_back", "تم التراجع"),
    ]

    from_version = models.CharField("من إصدار", max_length=40)
    to_version = models.CharField("إلى إصدار", max_length=40)
    update_type = models.CharField("نوع التحديث", max_length=20, choices=UPDATE_TYPE_CHOICES, default="optional")
    status = models.CharField("الحالة", max_length=20, choices=STATUS_CHOICES, default="pending")
    started_at = models.DateTimeField("بدأ في", null=True, blank=True)
    completed_at = models.DateTimeField("اكتمل في", null=True, blank=True)
    rollback_available = models.BooleanField("التراجع متاح", default=False)
    backup_id = models.CharField("معرّف النسخة الاحتياطية", max_length=100, blank=True, default="")

    class Meta:
        verbose_name = "سجل تحديث"
        verbose_name_plural = "سجل التحديثات"
        ordering = ["-started_at"]

    def __str__(self):
        return f"{self.from_version} → {self.to_version}"


class LicenseState(models.Model):
    """حالة ترخيص التطبيق (تجربة/مرخّص/قراءة فقط)."""

    MODE_CHOICES = [
        ("trial", "تجربة"),
        ("licensed", "مرخّص"),
        ("read_only", "قراءة فقط"),
    ]

    activation_date = models.DateTimeField("تاريخ التفعيل", default=timezone.now)
    trial_days = models.PositiveIntegerField("أيام التجربة", default=30)
    expires_at = models.DateTimeField("تاريخ الانتهاء", null=True, blank=True)
    is_trial = models.BooleanField("نسخة تجريبية", default=True)
    is_expired = models.BooleanField("منتهية", default=False)
    # مفتاح الترخيص مخزّن مُجزّأً (hashed) وليس كنص واضح
    license_key = models.CharField("مفتاح الترخيص (مجزّأ)", max_length=255, blank=True, default="")
    mode = models.CharField("الوضع", max_length=20, choices=MODE_CHOICES, default="trial")
    last_verified = models.DateTimeField("آخر تحقق", null=True, blank=True)

    class Meta:
        verbose_name = "حالة الترخيص"
        verbose_name_plural = "حالة الترخيص"

    def __str__(self):
        return f"{self.get_mode_display()} - تنتهي: {self.expires_at}"

    @property
    def trial_days_remaining(self):
        """عدد أيام التجربة المتبقية (0 إذا انتهت)."""
        if not self.expires_at:
            return 0
        delta = self.expires_at - timezone.now()
        return max(0, delta.days)


class BackupHistory(models.Model):
    """سجل النسخ الاحتياطي."""

    STATUS_CHOICES = [
        ("success", "ناجح"),
        ("failed", "فاشل"),
        ("in_progress", "قيد التنفيذ"),
    ]

    backup_type = models.CharField("نوع النسخة", max_length=40, default="manual")
    file_path = models.CharField("مسار الملف", max_length=500, blank=True, default="")
    file_size = models.BigIntegerField("حجم الملف", default=0)
    checksum = models.CharField("البصمة (checksum)", max_length=128, blank=True, default="")
    db_version = models.CharField("إصدار قاعدة البيانات", max_length=40, blank=True, default="")
    app_version = models.CharField("إصدار التطبيق", max_length=40, blank=True, default="")
    status = models.CharField("الحالة", max_length=20, choices=STATUS_CHOICES, default="in_progress")
    created_at = models.DateTimeField("تاريخ الإنشاء", auto_now_add=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name="أنشأها",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="backups",
    )
    notes = models.TextField("ملاحظات", blank=True, default="")

    class Meta:
        verbose_name = "نسخة احتياطية"
        verbose_name_plural = "سجل النسخ الاحتياطي"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.backup_type} @ {self.created_at}"


class ServerSettings(models.Model):
    """إعدادات الخادم المحلي."""

    port = models.PositiveIntegerField("المنفذ", default=8765)
    allow_network_access = models.BooleanField("السماح بالوصول عبر الشبكة", default=False)
    bind_address = models.CharField("عنوان الربط", max_length=40, default="127.0.0.1")
    max_connections = models.PositiveIntegerField("أقصى عدد اتصالات", default=50)
    last_updated = models.DateTimeField("آخر تحديث", auto_now=True)

    class Meta:
        verbose_name = "إعدادات الخادم"
        verbose_name_plural = "إعدادات الخادم"

    def __str__(self):
        return f"{self.bind_address}:{self.port}"
