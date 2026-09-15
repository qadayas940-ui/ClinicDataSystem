"""نماذج المختبر (المرحلة 3 — النماذج فقط الآن)."""
from django.conf import settings
from django.db import models

from apps.core.models import SoftDeleteModel


class LabOrder(SoftDeleteModel):
    """طلب فحص مخبري."""

    STATUS_CHOICES = [
        ("pending", "قيد الانتظار"),
        ("completed", "مكتمل"),
        ("cancelled", "ملغى"),
    ]

    patient = models.ForeignKey("patients.Patient", verbose_name="المريض", on_delete=models.PROTECT, related_name="lab_orders")
    visit = models.ForeignKey("visits.Visit", verbose_name="الزيارة", on_delete=models.SET_NULL, null=True, blank=True, related_name="lab_orders")
    order_date = models.DateTimeField("تاريخ الطلب")
    requesting_doctor = models.ForeignKey(settings.AUTH_USER_MODEL, verbose_name="الطبيب الطالب", on_delete=models.SET_NULL, null=True, blank=True, related_name="lab_orders")
    status = models.CharField("الحالة", max_length=20, choices=STATUS_CHOICES, default="pending")
    result_date = models.DateTimeField("تاريخ النتيجة", null=True, blank=True)
    notes = models.TextField("ملاحظات", blank=True, default="")

    class Meta:
        verbose_name = "طلب مخبري"
        verbose_name_plural = "الطلبات المخبرية"
        ordering = ["-order_date"]

    def __str__(self):
        return f"طلب مخبري {self.patient} @ {self.order_date}"


class LabOrderTest(SoftDeleteModel):
    """فحص ضمن طلب مخبري."""

    lab_order = models.ForeignKey(LabOrder, verbose_name="الطلب المخبري", on_delete=models.CASCADE, related_name="tests")
    test_code = models.CharField("رمز الفحص", max_length=40, blank=True, default="")
    test_name = models.CharField("اسم الفحص", max_length=200)
    result_value = models.CharField("النتيجة", max_length=120, blank=True, default="")
    unit = models.CharField("الوحدة", max_length=40, blank=True, default="")
    reference_range = models.CharField("المعدل المرجعي", max_length=120, blank=True, default="")
    is_abnormal = models.BooleanField("غير طبيعي", default=False)
    notes = models.CharField("ملاحظات", max_length=255, blank=True, default="")

    class Meta:
        verbose_name = "فحص مخبري"
        verbose_name_plural = "الفحوصات المخبرية"

    def __str__(self):
        return self.test_name
