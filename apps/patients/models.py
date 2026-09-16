"""
نماذج المرضى (المرحلة 2 — النماذج فقط الآن).

- Patient: السجل الأساسي للمريض (يستخدم UUID كمعرّف).
- PatientName / PatientContact / PatientAddress: بيانات مرتبطة بالمريض.
"""
import uuid

from django.conf import settings
from django.db import models
from django.utils import timezone

from apps.core.models import SoftDeleteModel


class Patient(SoftDeleteModel):
    """السجل الأساسي للمريض."""

    GENDER_CHOICES = [
        ("male", "ذكر"),
        ("female", "أنثى"),
        ("unknown", "غير محدد"),
    ]
    AGE_UNIT_CHOICES = [
        ("year", "سنة"),
        ("month", "شهر"),
        ("day", "يوم"),
    ]

    id = models.UUIDField("المعرّف", primary_key=True, default=uuid.uuid4, editable=False)
    internal_code = models.CharField("الرمز الداخلي", max_length=40, unique=True)
    primary_name = models.ForeignKey(
        "PatientName",
        verbose_name="الاسم الأساسي",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="primary_for",
    )
    gender = models.CharField("الجنس", max_length=10, choices=GENDER_CHOICES, default="unknown")
    date_of_birth = models.DateField("تاريخ الميلاد", null=True, blank=True)
    approx_age_value = models.PositiveIntegerField("العمر التقريبي", null=True, blank=True)
    approx_age_unit = models.CharField("وحدة العمر", max_length=10, choices=AGE_UNIT_CHOICES, blank=True, default="")
    approx_age_recorded_date = models.DateField("تاريخ تسجيل العمر التقريبي", null=True, blank=True)
    is_approx_age = models.BooleanField("عمر تقريبي", default=False)
    is_active = models.BooleanField("نشط", default=True)
    external_id = models.CharField("المعرّف الخارجي", max_length=120, blank=True, default="", db_index=True)
    source_type = models.CharField("نوع المصدر", max_length=40, blank=True, default="manual")
    source_file = models.CharField("ملف المصدر", max_length=255, blank=True, default="")
    source_sheet = models.CharField("ورقة المصدر", max_length=200, blank=True, default="")
    source_row = models.PositiveIntegerField("صف المصدر", null=True, blank=True)
    imported_at = models.DateTimeField("تاريخ الاستيراد", null=True, blank=True)
    additional_data = models.JSONField("البيانات الإضافية", default=dict, blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name="أنشأه",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_patients",
    )

    class Meta:
        verbose_name = "مريض"
        verbose_name_plural = "المرضى"
        ordering = ["-created_at"]

    def __str__(self):
        return self.internal_code

    @property
    def display_name(self):
        primary = self.primary_name or self.names.filter(is_primary=True).first() or self.names.first()
        return primary.full_name if primary else "مريض بلا اسم"

    @property
    def calculated_age(self):
        """العمر الحالي المشتق من الميلاد، أو العمر التقريبي مع وحدته."""
        if self.date_of_birth:
            today = timezone.localdate()
            years = today.year - self.date_of_birth.year - (
                (today.month, today.day) < (self.date_of_birth.month, self.date_of_birth.day)
            )
            return f"{max(0, years)} سنة"
        if self.approx_age_value is not None:
            labels = {"year": "سنة", "month": "شهر", "day": "يوم"}
            return f"{self.approx_age_value} {labels.get(self.approx_age_unit, '')}".strip()
        return "غير محدد"

    @property
    def latest_visit(self):
        return self.visits.select_related("department", "doctor_reference", "organizer_reference").first()

    @property
    def latest_source_row(self):
        return self.source_rows.select_related("sheet").order_by("-batch_id", "-original_row_number").first()


class PatientSequence(models.Model):
    """عداد سنوي آمن للرقم التعريفي الدائم للمريض."""

    year = models.PositiveSmallIntegerField("السنة", unique=True)
    last_value = models.PositiveBigIntegerField("آخر تسلسل", default=0)

    class Meta:
        verbose_name = "تسلسل أرقام المرضى"
        verbose_name_plural = "تسلسلات أرقام المرضى"

    def __str__(self):
        return f"{self.year}: {self.last_value}"


class PatientName(SoftDeleteModel):
    """أسماء المريض (قد يكون له أكثر من صيغة اسم)."""

    patient = models.ForeignKey(Patient, verbose_name="المريض", on_delete=models.CASCADE, related_name="names")
    full_name = models.CharField("الاسم الكامل", max_length=255, db_index=True)
    normalized_name = models.CharField("الاسم المطبّع للبحث", max_length=255, blank=True, default="", db_index=True)
    is_primary = models.BooleanField("أساسي", default=False)
    source = models.CharField("المصدر", max_length=80, blank=True, default="")

    class Meta:
        verbose_name = "اسم مريض"
        verbose_name_plural = "أسماء المرضى"
        ordering = ["-is_primary"]

    def __str__(self):
        return self.full_name

    def save(self, *args, **kwargs):
        from .services import normalize_arabic_text

        self.normalized_name = normalize_arabic_text(self.full_name)
        if kwargs.get("update_fields") is not None:
            kwargs["update_fields"] = set(kwargs["update_fields"]) | {"normalized_name"}
        super().save(*args, **kwargs)


class PatientContact(SoftDeleteModel):
    """وسيلة تواصل للمريض."""

    CONTACT_TYPE_CHOICES = [
        ("phone", "هاتف"),
        ("mobile", "جوال"),
        ("email", "بريد إلكتروني"),
    ]

    patient = models.ForeignKey(Patient, verbose_name="المريض", on_delete=models.CASCADE, related_name="contacts")
    contact_type = models.CharField("النوع", max_length=20, choices=CONTACT_TYPE_CHOICES, default="mobile")
    value = models.CharField("القيمة", max_length=120, db_index=True)
    is_primary = models.BooleanField("أساسي", default=False)
    notes = models.CharField("ملاحظات", max_length=255, blank=True, default="")

    class Meta:
        verbose_name = "وسيلة تواصل"
        verbose_name_plural = "وسائل التواصل"

    def __str__(self):
        return f"{self.get_contact_type_display()}: {self.value}"


class PatientAddress(SoftDeleteModel):
    """عنوان المريض."""

    patient = models.ForeignKey(Patient, verbose_name="المريض", on_delete=models.CASCADE, related_name="addresses")
    address_type = models.CharField("نوع العنوان", max_length=40, blank=True, default="")
    text = models.TextField("العنوان", blank=True, default="")
    city = models.CharField("المدينة", max_length=80, blank=True, default="")
    notes = models.CharField("ملاحظات", max_length=255, blank=True, default="")

    class Meta:
        verbose_name = "عنوان"
        verbose_name_plural = "العناوين"

    def __str__(self):
        return f"{self.city} - {self.text[:30]}"
