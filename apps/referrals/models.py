"""نماذج الإحالات (المرحلة 3 — النماذج فقط الآن)."""
from django.conf import settings
from django.db import models

from apps.core.models import SoftDeleteModel


class Referral(SoftDeleteModel):
    """إحالة مريض إلى جهة أخرى."""

    STATUS_CHOICES = [
        ("pending", "قيد الانتظار"),
        ("completed", "مكتملة"),
        ("cancelled", "ملغاة"),
    ]

    patient = models.ForeignKey("patients.Patient", verbose_name="المريض", on_delete=models.PROTECT, related_name="referrals")
    source_visit = models.ForeignKey("visits.Visit", verbose_name="الزيارة المصدر", on_delete=models.SET_NULL, null=True, blank=True, related_name="referrals")
    referring_doctor = models.ForeignKey(settings.AUTH_USER_MODEL, verbose_name="الطبيب المُحيل", on_delete=models.SET_NULL, null=True, blank=True, related_name="referrals")
    destination_name = models.CharField("جهة الإحالة", max_length=200)
    destination_type = models.CharField("نوع الجهة", max_length=80, blank=True, default="")
    reason = models.TextField("سبب الإحالة", blank=True, default="")
    referral_date = models.DateTimeField("تاريخ الإحالة")
    status = models.CharField("الحالة", max_length=20, choices=STATUS_CHOICES, default="pending")
    followup_notes = models.TextField("ملاحظات المتابعة", blank=True, default="")
    qr_code_data = models.CharField("بيانات رمز QR", max_length=500, blank=True, default="")

    class Meta:
        verbose_name = "إحالة"
        verbose_name_plural = "الإحالات"
        ordering = ["-referral_date"]

    def __str__(self):
        return f"إحالة {self.patient} → {self.destination_name}"


class ReferralFollowup(SoftDeleteModel):
    """متابعة لإحالة."""

    referral = models.ForeignKey(Referral, verbose_name="الإحالة", on_delete=models.CASCADE, related_name="followups")
    followup_date = models.DateTimeField("تاريخ المتابعة")
    notes = models.TextField("ملاحظات", blank=True, default="")
    status = models.CharField("الحالة", max_length=40, blank=True, default="")
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, verbose_name="أنشأها", on_delete=models.SET_NULL, null=True, blank=True, related_name="referral_followups")

    class Meta:
        verbose_name = "متابعة إحالة"
        verbose_name_plural = "متابعات الإحالات"
        ordering = ["-followup_date"]

    def __str__(self):
        return f"متابعة @ {self.followup_date}"
