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


class PatientName(SoftDeleteModel):
    """أسماء المريض (قد يكون له أكثر من صيغة اسم)."""

    patient = models.ForeignKey(Patient, verbose_name="المريض", on_delete=models.CASCADE, related_name="names")
    full_name = models.CharField("الاسم الكامل", max_length=255, db_index=True)
    is_primary = models.BooleanField("أساسي", default=False)
    source = models.CharField("المصدر", max_length=80, blank=True, default="")

    class Meta:
        verbose_name = "اسم مريض"
        verbose_name_plural = "أسماء المرضى"
        ordering = ["-is_primary"]

    def __str__(self):
        return self.full_name


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
