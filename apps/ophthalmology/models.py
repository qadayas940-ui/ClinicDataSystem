"""نماذج عيادة العيون (المرحلة 3 — النماذج فقط الآن)."""
from django.conf import settings
from django.db import models

from apps.core.models import SoftDeleteModel


class EyeClinicVisit(SoftDeleteModel):
    """زيارة عيادة العيون مع قياسات النظر وضغط العين."""

    STATUS_CHOICES = [
        ("open", "مفتوحة"),
        ("closed", "مغلقة"),
        ("cancelled", "ملغاة"),
    ]

    patient = models.ForeignKey("patients.Patient", verbose_name="المريض", on_delete=models.PROTECT, related_name="eye_visits")
    visit_date = models.DateTimeField("تاريخ الزيارة")
    doctor = models.ForeignKey(settings.AUTH_USER_MODEL, verbose_name="الطبيب", on_delete=models.SET_NULL, null=True, blank=True, related_name="eye_doctor_visits")
    organizer = models.ForeignKey(settings.AUTH_USER_MODEL, verbose_name="المنظّم", on_delete=models.SET_NULL, null=True, blank=True, related_name="eye_organized_visits")
    chief_complaint = models.TextField("الشكوى الرئيسية", blank=True, default="")
    diagnosis = models.TextField("التشخيص", blank=True, default="")
    visual_acuity_right = models.CharField("حدة الإبصار (يمين)", max_length=40, blank=True, default="")
    visual_acuity_left = models.CharField("حدة الإبصار (يسار)", max_length=40, blank=True, default="")
    iop_right = models.CharField("ضغط العين (يمين)", max_length=40, blank=True, default="")
    iop_left = models.CharField("ضغط العين (يسار)", max_length=40, blank=True, default="")
    notes = models.TextField("ملاحظات", blank=True, default="")
    status = models.CharField("الحالة", max_length=20, choices=STATUS_CHOICES, default="open")

    class Meta:
        verbose_name = "زيارة عيون"
        verbose_name_plural = "زيارات العيون"
        ordering = ["-visit_date"]

    def __str__(self):
        return f"زيارة عيون {self.patient} @ {self.visit_date}"
