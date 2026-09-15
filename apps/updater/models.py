"""نماذج التحديثات (المرحلة 6 — النماذج فقط الآن)."""
from django.db import models


class UpdateManifest(models.Model):
    """بيان تحديث متاح للتطبيق."""

    CHANNEL_CHOICES = [
        ("stable", "مستقر"),
        ("beta", "تجريبي"),
        ("develop", "تطوير"),
    ]
    UPDATE_TYPE_CHOICES = [
        ("optional", "اختياري"),
        ("recommended", "موصى به"),
        ("security", "أمني"),
    ]

    version = models.CharField("الإصدار", max_length=40)
    channel = models.CharField("القناة", max_length=20, choices=CHANNEL_CHOICES, default="stable")
    update_type = models.CharField("نوع التحديث", max_length=20, choices=UPDATE_TYPE_CHOICES, default="optional")
    download_url = models.URLField("رابط التنزيل", blank=True, default="")
    sha256 = models.CharField("بصمة SHA-256", max_length=64, blank=True, default="")
    min_supported_version = models.CharField("أدنى إصدار مدعوم", max_length=40, blank=True, default="")
    deadline = models.DateTimeField("الموعد النهائي", null=True, blank=True)
    message_ar = models.TextField("الرسالة (عربي)", blank=True, default="")
    is_mandatory = models.BooleanField("إلزامي", default=False)
    allow_postpone = models.BooleanField("السماح بالتأجيل", default=True)
    grace_period_days = models.PositiveIntegerField("فترة السماح (أيام)", default=0)
    checked_at = models.DateTimeField("تاريخ الفحص", auto_now=True)

    class Meta:
        verbose_name = "بيان تحديث"
        verbose_name_plural = "بيانات التحديث"
        ordering = ["-checked_at"]

    def __str__(self):
        return f"{self.version} ({self.get_channel_display()})"
