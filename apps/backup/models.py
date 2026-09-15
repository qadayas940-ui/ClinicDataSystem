"""
نماذج النسخ الاحتياطي (المرحلة 5 — النماذج فقط الآن).

السجل الرئيسي للنسخ الاحتياطي معرّف في apps.core.models.BackupHistory.
هنا نضيف جدولة النسخ الاحتياطي.
"""
from django.conf import settings
from django.db import models

from apps.core.models import SoftDeleteModel


class BackupSchedule(SoftDeleteModel):
    """جدولة النسخ الاحتياطي التلقائي."""

    FREQUENCY_CHOICES = [
        ("daily", "يومي"),
        ("weekly", "أسبوعي"),
        ("monthly", "شهري"),
    ]

    name = models.CharField("اسم الجدولة", max_length=120, default="نسخ احتياطي تلقائي")
    frequency = models.CharField("التكرار", max_length=20, choices=FREQUENCY_CHOICES, default="daily")
    time_of_day = models.TimeField("وقت التنفيذ", null=True, blank=True)
    destination_path = models.CharField("مسار الوجهة", max_length=500, blank=True, default="")
    retention_count = models.PositiveIntegerField("عدد النسخ المحتفظ بها", default=7)
    is_enabled = models.BooleanField("مفعّلة", default=True)
    last_run_at = models.DateTimeField("آخر تشغيل", null=True, blank=True)
    next_run_at = models.DateTimeField("التشغيل القادم", null=True, blank=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, verbose_name="أنشأها", on_delete=models.SET_NULL, null=True, blank=True, related_name="backup_schedules")

    class Meta:
        verbose_name = "جدولة نسخ احتياطي"
        verbose_name_plural = "جدولة النسخ الاحتياطي"

    def __str__(self):
        return f"{self.name} ({self.get_frequency_display()})"
