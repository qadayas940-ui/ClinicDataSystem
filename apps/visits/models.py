"""نماذج الزيارات (المرحلة 3 — النماذج فقط الآن)."""
from django.conf import settings
from django.db import models

from apps.core.models import SoftDeleteModel


class Visit(SoftDeleteModel):
    """زيارة مريض للعيادة."""

    STATUS_CHOICES = [
        ("open", "مفتوحة"),
        ("closed", "مغلقة"),
        ("cancelled", "ملغاة"),
    ]

    patient = models.ForeignKey("patients.Patient", verbose_name="المريض", on_delete=models.PROTECT, related_name="visits")
    visit_date = models.DateTimeField("تاريخ الزيارة")
    department = models.ForeignKey("core.Department", verbose_name="القسم", on_delete=models.SET_NULL, null=True, blank=True, related_name="visits")
    doctor = models.ForeignKey(settings.AUTH_USER_MODEL, verbose_name="الطبيب", on_delete=models.SET_NULL, null=True, blank=True, related_name="doctor_visits")
    organizer = models.ForeignKey(settings.AUTH_USER_MODEL, verbose_name="المنظّم", on_delete=models.SET_NULL, null=True, blank=True, related_name="organized_visits")
    doctor_reference = models.ForeignKey(
        "core.ReferenceValue", verbose_name="اسم الطبيب من السجل المرجعي",
        on_delete=models.SET_NULL, null=True, blank=True, related_name="doctor_visits",
        limit_choices_to={"category": "doctor"},
    )
    organizer_reference = models.ForeignKey(
        "core.ReferenceValue", verbose_name="اسم المنظّم من السجل المرجعي",
        on_delete=models.SET_NULL, null=True, blank=True, related_name="organized_reference_visits",
        limit_choices_to={"category": "organizer"},
    )
    status = models.CharField("الحالة", max_length=20, choices=STATUS_CHOICES, default="open")
    chief_complaint = models.TextField("الشكوى الرئيسية", blank=True, default="")
    diagnosis = models.TextField("التشخيص", blank=True, default="")
    notes = models.TextField("ملاحظات", blank=True, default="")
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, verbose_name="أنشأها", on_delete=models.SET_NULL, null=True, blank=True, related_name="created_visits")

    class Meta:
        verbose_name = "زيارة"
        verbose_name_plural = "الزيارات"
        ordering = ["-visit_date"]

    def __str__(self):
        return f"زيارة {self.patient} @ {self.visit_date}"


class VisitService(SoftDeleteModel):
    """خدمة مقدّمة ضمن زيارة."""

    visit = models.ForeignKey(Visit, verbose_name="الزيارة", on_delete=models.CASCADE, related_name="services")
    service_code = models.CharField("رمز الخدمة", max_length=40, blank=True, default="")
    service_name = models.CharField("اسم الخدمة", max_length=200)
    quantity = models.PositiveIntegerField("الكمية", default=1)
    notes = models.CharField("ملاحظات", max_length=255, blank=True, default="")

    class Meta:
        verbose_name = "خدمة زيارة"
        verbose_name_plural = "خدمات الزيارات"

    def __str__(self):
        return self.service_name
